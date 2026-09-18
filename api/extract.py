import json
import os
import re

import boto3

from api.common import BUCKET, REGION, new_id
from api.drugs import normalise_molecule
from api.frequency import parse_frequency
from api.models import Medicine, Molecule, Plan, RedFlags
from api.validate import GENERIC_RED_FLAG_TEXT

_textract = boto3.client("textract", region_name=REGION)
_bedrock = boto3.client("bedrock-runtime", region_name=REGION)
_s3 = boto3.client("s3", region_name=REGION)

MIN_WORDS_FOR_TEXTRACT = 20
CONFIDENCE_FLOOR = 0.85
UNITS = ("mg", "mcg", "g", "ml", "iu")
FOOD = ("before", "after", "unspecified")
IMAGE_FORMATS = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg"}

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
    res = _textract.analyze_document(
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


def _call_model(image_bytes, image_format, words, model_id):
    word_list = "\n".join("%s: %s" % (w["id"], w["text"]) for w in words)
    # Without a closing instruction after the word list Qwen3-VL returns the empty schema.
    content = [{"text": PROMPT + word_list + "\n\nNow return the JSON for this page, "
                "with one entry per medicine line."}]
    if image_bytes:
        content.insert(0, {"image": {"format": image_format, "source": {"bytes": image_bytes}}})
    res = _bedrock.converse(
        modelId=model_id or os.environ["BEDROCK_MODEL_ID"],
        messages=[{"role": "user", "content": content}],
        inferenceConfig={"maxTokens": 4000, "temperature": 0})
    text = "".join(c.get("text", "") for c in res["output"]["message"]["content"])
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("model returned no JSON")
    return json.loads(text[start:end + 1])


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _molecule(x):
    strength = _float(x.get("strengthMg"))
    unit = str(x.get("unit") or "").strip().lower()
    if strength is not None and unit in ("mcg", "g"):
        # Same canonical form as drugs.parse_composition, so Box Check compares like with like.
        strength, unit = (strength / 1000.0 if unit == "mcg" else strength * 1000.0), "mg"
    elif strength is None and unit not in UNITS:
        unit = "mg"
    return Molecule(name=normalise_molecule(x["name"]), strengthMg=strength, unit=unit)


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
    mols = [_molecule(x) for x in (m.get("molecules") or []) if x.get("name")]
    mols = [x for x in mols if x.name]
    duration = _float(m.get("durationDays"))
    block_ids = _valid_ids(m.get("sourceBlockIds"), words)
    cited = " ".join(w["text"] for w in words if w["id"] in block_ids).replace(",", "")
    printed = {float(n) for n in re.findall(r"\d+(?:\.\d+)?", cited)}
    # A strength the model states must be a number on the cited words, else it was inferred.
    unprinted = any(_float(x.get("strengthMg")) not in printed
                    for x in (m.get("molecules") or [])
                    if x.get("name") and _float(x.get("strengthMg")) is not None)
    confidence = _float(m.get("confidence")) or 0.0
    food = m.get("foodRelation")
    crop = crop_for(block_ids, words)
    if crop:
        crop["s3Key"] = key
    return Medicine(
        lineId="", rawText=m.get("rawText") or "", brand=m.get("brand"), molecules=mols,
        form=m.get("form"), frequency=frequency, slots=slots,
        foodRelation=food if food in FOOD else "unspecified",
        durationDays=None if duration is None else int(duration), prn=prn,
        prnCondition=m.get("prnCondition"), confidence=confidence,
        sourceBlockIds=block_ids, source=source, crop=crop,
        needsConfirmation=(confidence < CONFIDENCE_FLOOR or not mols or frequency is None
                           or (not slots and not prn) or source == "vision_only"
                           or not block_ids or unprinted))


def extract_plan(s3_keys, circle_id, model_id=None):
    medicines, red_flags, follow_up, patient = [], None, None, None

    for key in s3_keys:
        words = textract_words(key)
        source = "textract" if len(words) >= MIN_WORDS_FOR_TEXTRACT else "vision_only"
        image = _s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
        image_format = IMAGE_FORMATS.get(key.rsplit(".", 1)[-1].lower(), "jpeg")
        raw = _call_model(image, image_format, words, model_id)
        patient = patient or raw.get("patientName")

        for m in raw.get("medicines") or []:
            med = _medicine(m, words, source, key)
            med.lineId = "m%d" % (len(medicines) + 1)
            medicines.append(med)

        rf = raw.get("redFlags") or {}
        if rf.get("present") and rf.get("text") and red_flags is None:
            ids = _valid_ids(rf.get("sourceBlockIds"), words)
            if ids:
                red_flags = RedFlags(source="document", text=rf["text"], sourceBlockIds=ids)
        if isinstance(raw.get("followUp"), dict):
            follow_up = follow_up or raw["followUp"]

    if red_flags is None:
        red_flags = RedFlags(source="generic", text=GENERIC_RED_FLAG_TEXT, sourceBlockIds=[])

    return Plan(planId=new_id("pl"), circleId=circle_id, medicines=medicines,
                redFlags=red_flags, patientName=patient, followUp=follow_up)
