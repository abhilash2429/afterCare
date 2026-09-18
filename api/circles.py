import hashlib
import json
import os
import secrets
import time
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from api.auth import _table, issue_circle_token, principal_from_event, require
from api.common import new_id
from api.handler import respond, route
from api.models import DEFAULT_SLOT_TIMES

INVITE_TTL = 24 * 3600
LANGUAGES = ("en", "hi", "kn")


def _body(event):
    body = json.loads(event.get("body") or "{}")
    if not isinstance(body, dict):
        raise ValueError("body must be a JSON object")
    return body


def _invite_key(token):
    return {"PK": "INVITE#%s" % hashlib.sha256(token.encode()).hexdigest(), "SK": "META"}


@route("POST", "/circles")
def create_circle(event, params):
    principal = principal_from_event(event)
    if principal["role"] != "owner" or principal["circleId"] is not None:
        raise PermissionError("only a signed-in owner can create a circle")
    body = _body(event)
    name, language = body.get("name", "Family"), body.get("language", "kn")
    if not isinstance(name, str) or not 1 <= len(name) <= 100:
        raise ValueError("name must be 1-100 characters")
    if language not in LANGUAGES:
        raise ValueError("language must be one of en, hi, kn")

    circle_id = new_id("ci")
    member = {"PK": "CIRCLE#%s" % circle_id, "SK": "MEMBER#%s" % principal["sub"],
              "role": "owner"}
    if principal.get("email"):
        member["email"] = principal["email"]
    meta = {"PK": "CIRCLE#%s" % circle_id, "SK": "META", "circleId": circle_id, "name": name,
            "language": language, "slotTimes": dict(DEFAULT_SLOT_TIMES), "escalationMinutes": 30}
    table = _table()
    table.meta.client.transact_write_items(TransactItems=[
        {"Put": {"TableName": table.name, "ConditionExpression": "attribute_not_exists(PK)",
                 "Item": item}}
        for item in (meta, member)])
    return respond(201, {"circleId": circle_id})


@route("GET", "/circles/{circleId}")
def get_circle(event, params):
    circle_id = params["circleId"]
    principal = require(principal_from_event(event), circle_id)
    meta = _table().get_item(Key={"PK": "CIRCLE#%s" % circle_id, "SK": "META"}).get("Item")
    if not meta:
        return respond(404, {"code": "not_found", "message": "circle not found"})
    return respond(200, {"circleId": circle_id, "name": meta.get("name"),
                         "language": meta.get("language", "en"),
                         "slotTimes": meta.get("slotTimes") or dict(DEFAULT_SLOT_TIMES),
                         "escalationMinutes": int(meta.get("escalationMinutes", 30)),
                         "activePlanId": meta.get("activePlanId"),
                         "role": principal["role"]})


@route("POST", "/circles/{circleId}/invite")
def invite(event, params):
    circle_id = params["circleId"]
    require(principal_from_event(event), circle_id, roles=("owner",))
    token = secrets.token_urlsafe(24)
    expires = int(time.time()) + INVITE_TTL
    _table().put_item(Item={**_invite_key(token), "circleId": circle_id, "role": "caregiver",
                            "expiresAt": expires, "used": False})
    url = "%s/join?c=%s&t=%s" % (os.environ["WEB_ORIGIN"], circle_id, token)
    return respond(201, {"token": token, "url": url,
                         "expiresAt": datetime.fromtimestamp(expires, timezone.utc).isoformat()})


@route("POST", "/circles/{circleId}/join")
def join(event, params):
    circle_id = params["circleId"]
    token = _body(event).get("token")
    if not isinstance(token, str) or not token:
        raise ValueError("token is required")
    try:
        # Single atomic claim: TTL deletion is lazy, so expiry is checked here too.
        _table().update_item(
            Key=_invite_key(token),
            UpdateExpression="SET #u = :t",
            ConditionExpression="attribute_exists(PK) AND circleId = :c AND #u = :f "
                                "AND expiresAt > :now",
            ExpressionAttributeNames={"#u": "used"},
            ExpressionAttributeValues={":t": True, ":f": False, ":c": circle_id,
                                       ":now": int(time.time())})
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        return respond(404, {"code": "not_found", "message": "invite not valid"})
    sub = new_id("cg")
    _table().put_item(Item={"PK": "CIRCLE#%s" % circle_id, "SK": "MEMBER#%s" % sub,
                            "role": "caregiver"})
    return respond(200, {"sessionToken": issue_circle_token(circle_id, "caregiver", sub=sub),
                         "role": "caregiver", "circleId": circle_id})
