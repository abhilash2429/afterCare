import json
import os
import secrets
import time
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from api.auth import _table, issue_circle_token, principal_from_event, require
from api.common import new_id
from api.handler import respond, route

INVITE_TTL = 24 * 3600


@route("POST", "/circles/{circleId}/invite")
def invite(event, params):
    circle_id = params["circleId"]
    require(principal_from_event(event), circle_id, roles=("owner",))
    token = secrets.token_urlsafe(24)
    expires = int(time.time()) + INVITE_TTL
    _table().put_item(Item={"PK": "INVITE#%s" % token, "SK": "META", "circleId": circle_id,
                            "role": "caregiver", "expiresAt": expires, "used": False})
    url = "%s/join?c=%s&t=%s" % (os.environ["WEB_ORIGIN"], circle_id, token)
    return respond(201, {"token": token, "url": url,
                         "expiresAt": datetime.fromtimestamp(expires, timezone.utc).isoformat()})


@route("POST", "/circles/{circleId}/join")
def join(event, params):
    circle_id = params["circleId"]
    token = json.loads(event.get("body") or "{}").get("token")
    if not isinstance(token, str) or not token:
        raise ValueError("token is required")
    try:
        # Single atomic claim: TTL deletion is lazy, so expiry is checked here too.
        _table().update_item(
            Key={"PK": "INVITE#%s" % token, "SK": "META"},
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
