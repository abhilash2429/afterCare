import json
import time

import boto3
from botocore.exceptions import ClientError

from api.auth import principal_from_event, require
from api.common import BUCKET, REGION, TABLE, new_id, now_ist
from api.extract import ExtractionFailed, extract_plan
from api.handler import respond, route
import api.plans as plans

_s3 = boto3.client("s3", region_name=REGION)
_ddb = boto3.resource("dynamodb", region_name=REGION)

ALLOWED_TYPES = ("image/jpeg", "image/png")
_EXT = {"image/jpeg": "jpg", "image/png": "png"}


def _body(event):
    body = json.loads(event.get("body") or "{}")
    if not isinstance(body, dict):
        raise ValueError("body must be a JSON object")
    return body


def _resolve_circle_id(explicit, principal):
    circle_id = explicit or principal.get("circleId")
    if not circle_id:
        raise ValueError("circleId is required")
    return circle_id


@route("POST", "/documents")
def create_document(event, params):
    body = _body(event)
    principal = principal_from_event(event)
    circle_id = _resolve_circle_id(body.get("circleId"), principal)
    require(principal, circle_id)
    try:
        pages = int(body.get("pageCount", 1))
    except (TypeError, ValueError):
        raise ValueError("circleId, pageCount 1-10 and a supported contentType are required")
    content_type = body.get("contentType", "image/jpeg")
    if not circle_id or not 1 <= pages <= 10 or content_type not in ALLOWED_TYPES:
        raise ValueError("circleId, pageCount 1-10 and a supported contentType are required")

    document_id = new_id("doc")
    ext = _EXT[content_type]
    uploads = []
    for page in range(1, pages + 1):
        key = "circles/%s/%s/p%d.%s" % (circle_id, document_id, page, ext)
        uploads.append({"page": page, "key": key, "uploadUrl": _s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": BUCKET, "Key": key, "ContentType": content_type},
            ExpiresIn=900)})

    _ddb.Table(TABLE).put_item(Item={
        "PK": "CIRCLE#%s" % circle_id, "SK": "DOC#%s" % document_id,
        "documentId": document_id, "circleId": circle_id,
        "keys": [u["key"] for u in uploads],
        "pageCount": pages, "contentType": content_type,
        "uploadedBy": principal.get("sub"),
        "createdAt": now_ist().isoformat(),
        "expiresAt": int(time.time()) + 30 * 24 * 3600})
    return respond(201, {"documentId": document_id, "uploads": uploads})


@route("POST", "/documents/{documentId}/extract")
def extract(event, params):
    body = _body(event)
    principal = principal_from_event(event)
    circle_id = _resolve_circle_id(body.get("circleId"), principal)
    require(principal, circle_id, roles=("owner",))
    doc = _ddb.Table(TABLE).get_item(
        Key={"PK": "CIRCLE#%s" % circle_id, "SK": "DOC#%s" % params["documentId"]}
    ).get("Item")
    if not doc:
        return respond(404, {"code": "not_found", "message": "document not found"})

    if doc.get("planId"):
        existing = plans._load(circle_id, doc["planId"])
        if existing is not None:
            return respond(200, existing.to_dict())

    try:
        plan = extract_plan(doc.get("keys") or [], circle_id)
    except ClientError as exc:
        raise ExtractionFailed(str(exc) or "extraction failed") from exc
    plan.status = "draft"
    plan.sourceDocumentIds = [params["documentId"]]
    plans._save(plan)
    _ddb.Table(TABLE).update_item(
        Key={"PK": "CIRCLE#%s" % circle_id, "SK": "DOC#%s" % params["documentId"]},
        UpdateExpression="SET planId = :p",
        ExpressionAttributeValues={":p": plan.planId})
    return respond(200, plan.to_dict())
