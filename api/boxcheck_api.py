import json

import boto3

from api import plans
from api.auth import principal_from_event, require
from api.boxcheck import Strip, check_box
from api.common import BUCKET, REGION, TABLE
from api.drugs import parse_composition
from api.drugs_repo import lookup_brand
from api.extract import IMAGE_FORMATS, _call_model, _tokens, textract_words
from api.handler import respond, route

_s3 = boto3.client("s3", region_name=REGION)
_ddb = boto3.resource("dynamodb", region_name=REGION)

STRIP_PROMPT = """This photo shows medicine strips or bottles from an Indian pharmacy.
For each distinct strip, return JSON: {"strips":[{"brandText":null,"compositionText":null}]}
- brandText: the large brand name printed on the strip, or null if unreadable.
- compositionText: the composition line printed in small text, verbatim, e.g.
  "Aspirin (75mg)" or "Amoxycillin (500mg) + Clavulanic Acid (125mg)", or null.
Never guess either field. Return JSON only.
"""


def _read_strips(image_bytes, image_format):
    return _call_model(image_bytes, image_format, [], None, prompt=STRIP_PROMPT)


def _grounded(text, photo_tokens):
    if not text:
        return None
    toks = set(_tokens(text))
    if not toks:
        return None
    return text if toks <= photo_tokens else None


@route("POST", "/boxcheck")
def boxcheck(event, params):
    body = json.loads(event.get("body") or "{}")
    if not isinstance(body, dict):
        raise ValueError("body must be a JSON object")
    principal = principal_from_event(event)
    circle_id = body.get("circleId") or principal.get("circleId")
    if not circle_id:
        raise ValueError("circleId is required")
    require(principal, circle_id, roles=("owner", "caregiver"))
    plan_id = body.get("planId")
    document_id = body.get("documentId")
    if not plan_id or not document_id:
        raise ValueError("planId and documentId are required")
    plan = plans._load(circle_id, plan_id)
    doc = _ddb.Table(TABLE).get_item(
        Key={"PK": "CIRCLE#%s" % circle_id,
             "SK": "DOC#%s" % document_id}).get("Item")
    if not plan or not doc:
        return respond(404, {"code": "not_found", "message": "plan or document not found"})
    strips = []
    for key in doc.get("keys") or []:
        ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
        if ext not in IMAGE_FORMATS:
            raise ValueError("unsupported image extension: .%s" % ext)
        image_format = IMAGE_FORMATS[ext]
        words = textract_words(key)
        photo_tokens = set(t for w in words for t in _tokens(w.get("text", "")))
        image = _s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
        raw = _read_strips(image, image_format) or {}
        for s in raw.get("strips", []):
            trusted_comp = _grounded(s.get("compositionText"), photo_tokens)
            trusted_brand = _grounded(s.get("brandText"), photo_tokens)
            molecules = parse_composition(trusted_comp or "")
            if not molecules and trusted_brand:
                molecules = lookup_brand(trusted_brand)
            strips.append(Strip(brandText=trusted_brand, molecules=molecules))
    return respond(200, {"items": check_box(plan.medicines, strips)})
