import hashlib
import json

import boto3
from botocore.exceptions import ClientError

from api.auth import principal_from_event, require
from api.circles import LANGUAGES
from api.common import BUCKET, REGION, TABLE
from api.handler import respond, route
from api.models import Plan

_translate = boto3.client("translate", region_name=REGION)
_polly = boto3.client("polly", region_name=REGION)
_s3 = boto3.client("s3", region_name=REGION)
_ddb = boto3.resource("dynamodb", region_name=REGION)

# Kajal is a bilingual Indian neural voice; language is picked by LanguageCode, not VoiceId.
VOICE_ID = "Kajal"
LANG_CODE = {"hi": "hi-IN", "en": "en-IN"}
SLOT_WORDS = {"morning": "morning", "noon": "afternoon",
              "night": "night", "bedtime": "bedtime"}
FOOD_WORDS = {"before": "before food", "after": "after food"}


def translate_text(text, lang):
    if not text or lang == "en":
        return text
    return _translate.translate_text(Text=text, SourceLanguageCode="en",
                                     TargetLanguageCode=lang)["TranslatedText"]


def spoken_schedule(plan, tr=lambda text: text):
    """`tr` translates only the slot/food wording; drug names are spliced in untranslated."""
    lines = []
    for slot, word in SLOT_WORDS.items():
        meds = [m for m in plan.medicines if slot in m.slots]
        if not meds:
            continue
        # Each food relation is its own sentence: one slot can mix before- and after-food.
        for food in ("before food", "after food", None):
            group = [m for m in meds if FOOD_WORDS.get(m.foodRelation) == food]
            if not group:
                continue
            names = ", ".join(m.brand or (m.molecules[0].name if m.molecules else "") for m in group)
            lines.append("%s: %s." % (tr("In the %s%s" % (word, ", " + food if food else "")),
                                      names))
    return " ".join(lines)


def translate_plan(plan, lang):
    """Localised strings for the schedule screen: a label per slot in use and one
    instruction line per medicine. Brand/molecule names are left untranslated —
    a generic translate service cannot be trusted with drug names — only the
    surrounding wording (slot, food relation) is translated, and each distinct
    phrase is translated at most once per call via `cache`."""
    cache = {}

    def tr(text):
        if not text or lang == "en":
            return text
        if text not in cache:
            cache[text] = translate_text(text, lang)
        return cache[text]

    slots_used = {s for m in plan.medicines for s in m.slots}
    medicines = {}
    for m in plan.medicines:
        name = m.brand or (m.molecules[0].name if m.molecules else "")
        parts = [tr(SLOT_WORDS[s]) for s in m.slots if s in SLOT_WORDS]
        line = "%s: %s" % (", ".join(parts), name) if parts else name
        food = tr(FOOD_WORDS.get(m.foodRelation, ""))
        if food:
            line = "%s (%s)" % (line, food)
        medicines[m.lineId] = line
    return {"slots": {s: tr(SLOT_WORDS[s]) for s in slots_used},
            "medicines": medicines}


@route("GET", "/plans/{planId}/audio")
def audio(event, params):
    q = event.get("queryStringParameters") or {}
    lang = q.get("lang", "hi")
    if lang not in LANGUAGES:
        raise ValueError("lang must be one of en, hi, kn")

    principal = principal_from_event(event)
    circle_id = q.get("circleId") or principal.get("circleId")
    if not circle_id:
        raise ValueError("circleId is required")
    require(principal, circle_id)

    item = _ddb.Table(TABLE).get_item(
        Key={"PK": "CIRCLE#%s" % circle_id, "SK": "PLAN#%s" % params["planId"]}).get("Item")
    if not item:
        return respond(404, {"code": "not_found", "message": "plan not found"})

    plan = Plan.from_dict(json.loads(json.dumps(item, default=str)))
    # Polly has no Kannada voice: Kannada users hear Hindi audio (spec section 4).
    speak_lang = "hi" if lang in ("hi", "kn") else "en"
    cache = {}

    def tr(text):
        if text not in cache:
            cache[text] = translate_text(text, speak_lang)
        return cache[text]

    spoken = spoken_schedule(plan, tr)

    key = "audio/%s-%s.mp3" % (params["planId"],
                               hashlib.sha256(spoken.encode()).hexdigest()[:10])
    try:
        _s3.head_object(Bucket=BUCKET, Key=key)
    except ClientError:
        mp3 = _polly.synthesize_speech(Text=spoken, OutputFormat="mp3", VoiceId=VOICE_ID,
                                       Engine="neural", LanguageCode=LANG_CODE[speak_lang])
        _s3.put_object(Bucket=BUCKET, Key=key, Body=mp3["AudioStream"].read(),
                       ContentType="audio/mpeg")
    url = _s3.generate_presigned_url("get_object",
                                     Params={"Bucket": BUCKET, "Key": key}, ExpiresIn=3600)
    return respond(200, {"url": url, "spokenLanguage": speak_lang, "text": spoken})
