import json
import math
import os
import re

import boto3

from api.common import BUCKET, REGION, new_id
from api.drugs import _STRENGTH, normalise_brand, normalise_molecule
from api.drugs_repo import lookup_brand
from api.frequency import parse_frequency
from api.models import Medicine, Molecule, Plan, RedFlags
from api.validate import GENERIC_RED_FLAG_TEXT

_textract = None
_bedrock = None
_s3 = None


def _textract_client():
    global _textract
    if _textract is None:
        _textract = boto3.client("textract", region_name=REGION)
    return _textract


def _bedrock_client():
    global _bedrock
    if _bedrock is None:
        _bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    return _bedrock


def _s3_client():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=REGION)
    return _s3


MIN_WORDS_FOR_TEXTRACT = 20
CONFIDENCE_FLOOR = 0.85
UNITS = ("mg", "mcg", "g", "ml", "iu")
FOOD = ("before", "after", "unspecified")
IMAGE_FORMATS = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg"}
_FOOD_WORD = re.compile(r"\b(before|after|empty\s*stomach|ac|pc)\b", re.I)
_DURATION_WORD = re.compile(r"(\d+(?:\.\d+)?)\s*(day|days|week|weeks|month|months)\b", re.I)
_DURATION_MULT = {"day": 1, "days": 1, "week": 7, "weeks": 7, "month": 30, "months": 30}


class ExtractionFailed(ValueError):
    """The model's response was unusable: truncated output or not valid JSON."""


PROMPT = """You are reading an Indian hospital discharge summary or OPD prescription.

Below is the exact word list extracted from the page, each with an id.
Return ONLY JSON matching this schema:

{"medicines":[{"lineId":"m1","rawText":"","brand":null,
"molecules":[{"name":"","strengthMg":null,"unit":"mg|mcg|g|ml|iu"}],
"form":null,"frequency":null,"foodRelation":"before|after|unspecified","durationDays":null,
"prn":false,"prnCondition":null,"confidence":0.0,"sourceBlockIds":[]}],
"redFlags":{"present":false,"text":"","sourceBlockIds":[]},
"followUp":{"date":null,"with":null,"confidence":0.0},
"patientName":null}

HARD RULES:
- Copy values from the page. NEVER infer, complete or correct a missing value.
- If a strength, frequency or duration is not written on the page, use null.
- brand is the trade name as written ("T. Dolo 650 mg" -> "Dolo 650"), null when the
  line names only a generic.
- molecule name = the generic name as printed on Indian packs (aspirin not
  acetylsalicylic acid, paracetamol not acetaminophen, salbutamol not albuterol).
  A molecule name is never the brand. If the line names only a brand, give the
  generic(s) that brand contains, and lower confidence if you are not certain.
- strengthMg is the number printed for that molecule and unit is its printed unit
  (for syrups, the amount per stated volume: "1 mg/5 ml" is 1 with unit mg).
  A duration ("x 30 days") is never a strength.
- durationDays is the written duration in days (x 3 months = 90, x 2 weeks = 14).
- foodRelation: "after" for after food/meals; "before" for before food/meals/breakfast
  or empty stomach; "unspecified" when the line says neither.
- frequency must be copied verbatim as written (OD, BD, TDS, HS, SOS, 1-0-1, ...),
  without the dose amount ("2.5 ml TDS" -> "TDS").
- Do NOT convert frequency into times of day. That is done elsewhere.
- sourceBlockIds must list the word ids you read each medicine from. Never invent ids.
- redFlags.present is true ONLY if the page contains an explicit warning-signs or
  "report immediately" section. Copy it verbatim. Never write your own.
- confidence is your own 0-1 reading confidence for that line.

WORDS:
"""


def textract_words(s3_key):
    res = _textract_client().analyze_document(
        Document={"S3Object": {"Bucket": BUCKET, "Name": s3_key}},
        FeatureTypes=["TABLES", "LAYOUT"])
    words = []
    for block in res.get("Blocks", []):
        if block.get("BlockType") == "WORD":
            words.append({"id": block["Id"][:8], "text": block.get("Text", ""),
                          "box": block["Geometry"]["BoundingBox"]})
    return words


def crop_for(block_ids, words):
    wanted = set(block_ids)
    boxes = [w["box"] for w in words if w["id"] in wanted]
    if not boxes:
        return None
    left = min(b["Left"] for b in boxes)
    top = min(b["Top"] for b in boxes)
    right = max(b["Left"] + b["Width"] for b in boxes)
    bottom = max(b["Top"] + b["Height"] for b in boxes)
    pad = 0.01
    x, y = max(0.0, left - pad), max(0.0, top - pad)
    return {"x": x, "y": y, "w": min(1.0, right + pad) - x, "h": min(1.0, bottom + pad) - y}


def _call_model(image_bytes, image_format, words, model_id, prompt=PROMPT):
    word_list = "\n".join("%s: %s" % (w["id"], w["text"]) for w in words)
    # Without a closing instruction after the word list Qwen3-VL returns the empty schema.
    content = [{"text": prompt + word_list + "\n\nNow return the JSON for this page, "
                "with one entry per medicine line."}]
    if image_bytes:
        content.insert(0, {"image": {"format": image_format, "source": {"bytes": image_bytes}}})
    res = _bedrock_client().converse(
        modelId=model_id or os.environ["BEDROCK_MODEL_ID"],
        messages=[{"role": "user", "content": content}],
        inferenceConfig={"maxTokens": 4000, "temperature": 0})
    if res.get("stopReason") == "max_tokens":
        raise ExtractionFailed("model output was truncated (stopReason=max_tokens)")
    text = "".join(c.get("text", "") for c in res["output"]["message"]["content"])
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ExtractionFailed("model returned no JSON")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        raise ExtractionFailed("model returned unparseable JSON") from e


def _float(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _convert_strength(strength, unit):
    """mcg/g -> mg, the same canonical form drugs.parse_composition uses, so Box Check
    compares like with like."""
    unit = (unit or "").strip().lower()
    if strength is not None and unit in ("mcg", "g"):
        return (strength / 1000.0 if unit == "mcg" else strength * 1000.0), "mg"
    if strength is None and unit not in UNITS:
        unit = "mg"
    return strength, unit


def _molecule(x):
    strength, unit = _convert_strength(_float(x.get("strengthMg")),
                                       str(x.get("unit") or "").strip().lower())
    return Molecule(name=normalise_molecule(x["name"]), strengthMg=strength, unit=unit)


def _printed_names(text):
    """Every run of 1-5 consecutive words on the line, normalised like a molecule name."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {normalise_molecule(" ".join(tokens[i:i + n]))
            for n in range(1, 6) for i in range(len(tokens) - n + 1)}


def _tokens(text):
    return re.findall(r"[a-z0-9]+", str(text or "").lower())


def _printed_strengths(cited, brand):
    """(value_mg, unit) pairs that are actually printed as a strength on the page: a
    number next to a unit (api.drugs._STRENGTH - the same pattern the drugs dataset is
    built with; the unit may be the next token), or a bare number glued to the brand name
    ("Ecosprin 75"). A bare digit from a frequency pattern (1-0-1) or a duration
    ("x 5 days") is never a strength."""
    out = [_convert_strength(float(v), u.lower().replace(".", ""))
           for v, u in re.findall(_STRENGTH, cited, re.I)]
    brand = str(brand or "").strip()
    if brand:
        m = re.search(re.escape(brand) + r"\s+(\d+(?:\.\d+)?)\b(?!\s*-\s*\d)", cited, re.I)
        if m:
            out.append((float(m.group(1)), "mg"))
    return out


def _strength_is_printed(strength, unit, printed):
    return any(abs(strength - p_val) < 1e-6 and unit == p_unit for p_val, p_unit in printed)


def _frequency_is_printed(frequency, cited_tokens):
    tokens = _tokens(frequency)
    return bool(tokens) and all(t in cited_tokens for t in tokens)


def _duration_is_printed(duration, cited):
    return any(abs(duration - float(n) * _DURATION_MULT[word.lower()]) < 1e-6
               for n, word in _DURATION_WORD.findall(cited))


def _is_brand_echo(mol_name, brand_norm, brand_tokens):
    """True when the model just echoed the brand name back as the 'molecule'."""
    n = normalise_molecule(mol_name)
    return bool(brand_norm) and (n == brand_norm or n in brand_tokens)


def _dataset_molecules(brand, page):
    """Brand-only line: molecules from the dataset, strengths only as printed on the page.
    The dataset strength is used to pair a printed strength with a molecule, never copied."""
    found = lookup_brand(brand) if brand else []
    out = []
    for d in found:
        if len(found) == 1 and len(page) == 1:
            match = page[0]
        else:
            match = next((p for p in page if d.strengthMg is not None and p.unit == d.unit
                          and abs(p.strengthMg - d.strengthMg) < 1e-6), None)
        out.append(Molecule(name=normalise_molecule(d.name),
                            strengthMg=match.strengthMg if match else None,
                            unit=match.unit if match else (d.unit or "mg")))
    return out


def _valid_ids(ids, words):
    known = {w["id"] for w in words}
    return [b for b in (ids or []) if b in known]


def _medicine(m, words, source, key):
    frequency = m.get("frequency")
    frequency = None if frequency is None else str(frequency)
    slots, prn_word = parse_frequency(frequency or "")
    prn = bool(m.get("prn") or prn_word)
    if prn:
        slots = []
    duration = _float(m.get("durationDays"))
    block_ids = _valid_ids(m.get("sourceBlockIds"), words)
    cited_words = [w["text"] for w in words if w["id"] in block_ids]
    # R50: rawText is the verbatim cited words in reading order, never the model's prose.
    raw_text = " ".join(cited_words) if block_ids else (m.get("rawText") or "")
    cited = " ".join(cited_words).replace(",", "")
    cited_tokens = set(_tokens(cited))
    raw_mols = [x for x in (m.get("molecules") or []) if x.get("name")]
    # "Calcium carbonate 1250 mg (eq. to elemental calcium 500 mg)" is one drug; the
    # elemental clause restates the salt, it is not a second active ingredient.
    salts = [x for x in raw_mols
             if not str(x["name"]).strip().lower().startswith("elemental ")]
    if salts:
        raw_mols = salts
    printed_strengths = _printed_strengths(cited, m.get("brand"))

    def _mol_is_printed(x):
        s = _float(x.get("strengthMg"))
        if s is None:
            return True
        cs, cu = _convert_strength(s, str(x.get("unit") or "").strip().lower())
        return _strength_is_printed(cs, cu, printed_strengths)

    # A strength the model states must be a strength-shaped token on the page, else it
    # was inferred (C1): never a frequency digit (1-0-1), a duration digit ("x 5 days")
    # or a date, and its unit must match the printed unit after the same conversion.
    unprinted = any(not _mol_is_printed(x) for x in raw_mols)

    # R45/I4: a generic is trusted only if it is printed on the page AND is not just the
    # brand name echoed back as the "molecule"; otherwise the line is brand-only and its
    # molecules come from the drugs dataset, never from model memory.
    names = _printed_names(cited)
    brand_norm = normalise_brand(m.get("brand"))
    brand_tokens = set(brand_norm.split())
    brand_only = (not raw_mols
                  or not all(normalise_molecule(x["name"]) in names for x in raw_mols)
                  or any(_is_brand_echo(x["name"], brand_norm, brand_tokens)
                        for x in raw_mols))
    if brand_only:
        page = [_molecule(x) for x in raw_mols
                if _float(x.get("strengthMg")) is not None and _mol_is_printed(x)]
        mols = _dataset_molecules(m.get("brand"), page)
    else:
        mols = [x for x in map(_molecule, raw_mols) if x.name]

    confidence = _float(m.get("confidence")) or 0.0
    confidence = max(0.0, min(1.0, confidence))
    food = m.get("foodRelation")
    food = food if food in FOOD else "unspecified"
    # I2: frequency, duration and food are trusted only if the page backs them up.
    freq_unprinted = frequency is not None and not _frequency_is_printed(frequency, cited_tokens)
    duration_unprinted = duration is not None and not _duration_is_printed(duration, cited)
    food_unprinted = food != "unspecified" and not _FOOD_WORD.search(cited)
    crop = crop_for(block_ids, words)
    if crop:
        crop["s3Key"] = key
    return Medicine(
        lineId="", rawText=raw_text, brand=m.get("brand"), molecules=mols,
        form=m.get("form"), frequency=frequency, slots=slots,
        foodRelation=food,
        durationDays=None if duration is None else int(duration), prn=prn,
        prnCondition=m.get("prnCondition"), confidence=confidence,
        sourceBlockIds=block_ids, source=source, crop=crop,
        needsConfirmation=(confidence < CONFIDENCE_FLOOR or not mols or frequency is None
                           or (not slots and not prn) or source == "vision_only"
                           or not block_ids or unprinted or brand_only
                           # I1/R49: an unread strength or (non-PRN) duration is never trusted.
                           or any(x.strengthMg is None for x in mols)
                           or (duration is None and not prn)
                           or freq_unprinted or duration_unprinted or food_unprinted))


def extract_plan(s3_keys, circle_id, model_id=None):
    medicines, red_flags, follow_up, patient = [], None, None, None

    for key in s3_keys:
        ext = key.rsplit(".", 1)[-1].lower()
        if ext not in IMAGE_FORMATS:
            raise ValueError("unsupported image extension: .%s" % ext)
        image_format = IMAGE_FORMATS[ext]
        words = textract_words(key)
        source = "textract" if len(words) >= MIN_WORDS_FOR_TEXTRACT else "vision_only"
        image = _s3_client().get_object(Bucket=BUCKET, Key=key)["Body"].read()
        raw = _call_model(image, image_format, words, model_id)
        patient = patient or raw.get("patientName")

        for m in raw.get("medicines") or []:
            med = _medicine(m, words, source, key)
            med.lineId = "m%d" % (len(medicines) + 1)
            medicines.append(med)

        rf = raw.get("redFlags") or {}
        if rf.get("present") and rf.get("text") and red_flags is None:
            ids = _valid_ids(rf.get("sourceBlockIds"), words)
            cited_rf = " ".join(w["text"] for w in words if w["id"] in ids)
            # I3: keep it only if the model's text is actually on the page; an invented
            # warning, even with valid ids, falls back to the generic text.
            if ids and set(_tokens(rf["text"])) <= set(_tokens(cited_rf)):
                red_flags = RedFlags(source="document", text=rf["text"], sourceBlockIds=ids)
        if isinstance(raw.get("followUp"), dict):
            follow_up = follow_up or raw["followUp"]

    if red_flags is None:
        red_flags = RedFlags(source="generic", text=GENERIC_RED_FLAG_TEXT, sourceBlockIds=[])

    return Plan(planId=new_id("pl"), circleId=circle_id, medicines=medicines,
                redFlags=red_flags, patientName=patient, followUp=follow_up)
