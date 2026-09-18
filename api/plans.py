import json
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from api.auth import principal_from_event, require
from api.common import IST, REGION, TABLE, now_ist
from api.doses import build_doses
from api.handler import respond, route
from api.models import Plan
from api.schedules import create_dose_schedules
from api.validate import can_activate, validate_edit

_ddb = boto3.resource("dynamodb", region_name=REGION)


def _load(circle_id, plan_id):
    item = _ddb.Table(TABLE).get_item(
        Key={"PK": "CIRCLE#%s" % circle_id, "SK": "PLAN#%s" % plan_id}).get("Item")
    return Plan.from_dict(json.loads(json.dumps(item, default=str))) if item else None


def _save(plan):
    item = plan.to_dict()
    item.update({"PK": "CIRCLE#%s" % plan.circleId, "SK": "PLAN#%s" % plan.planId})
    _ddb.Table(TABLE).put_item(Item=json.loads(json.dumps(item), parse_float=str))


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


def _write_audit(circle_id, principal, original, edited):
    orig_by = {m["lineId"]: m for m in original.to_dict().get("medicines", [])}
    edit_by = {m["lineId"]: m for m in edited.to_dict().get("medicines", [])}
    line_ids = [lid for lid in edit_by
                if lid not in orig_by or orig_by[lid] != edit_by[lid]]
    now = datetime.now(timezone.utc)
    item = {
        "PK": "CIRCLE#%s" % circle_id,
        "SK": "AUDIT#%s#%s" % (now.isoformat(), edited.planId),
        "by": principal.get("sub"),
        "lineIds": line_ids,
        "before": [orig_by[lid] for lid in line_ids if lid in orig_by],
        "after": [edit_by[lid] for lid in line_ids],
        "expiresAt": int(time.time()) + 30 * 24 * 3600,
    }
    _ddb.Table(TABLE).put_item(
        Item=json.loads(json.dumps(item, default=str), parse_float=str))


@route("GET", "/plans/{planId}")
def get_plan(event, params):
    principal = principal_from_event(event)
    query = event.get("queryStringParameters") or {}
    circle_id = _resolve_circle_id(query.get("circleId"), principal)
    require(principal, circle_id)
    plan = _load(circle_id, params["planId"])
    if plan is None:
        return respond(404, {"code": "not_found", "message": "plan not found"})
    return respond(200, plan.to_dict())


@route("PATCH", "/plans/{planId}")
def patch_plan(event, params):
    body = _body(event)
    principal = principal_from_event(event)
    circle_id = _resolve_circle_id(body.get("circleId"), principal)
    require(principal, circle_id, roles=("owner",))
    original = _load(circle_id, params["planId"])
    if original is None:
        return respond(404, {"code": "not_found", "message": "plan not found"})

    edited = Plan.from_dict({**original.to_dict(),
                             "medicines": body.get("medicines", []),
                             "language": body.get("language", original.language),
                             "slotTimes": body.get("slotTimes", original.slotTimes)})
    user_edited = bool(body.get("userEdited"))
    errors = validate_edit(original, edited, user_edited)
    if errors:
        return respond(422, {"code": "validation_failed", "message": "; ".join(errors)})
    if user_edited:
        _write_audit(circle_id, principal, original, edited)
    _save(edited)
    return respond(200, edited.to_dict())


@route("POST", "/plans/{planId}/activate")
def activate_plan(event, params):
    body = _body(event)
    principal = principal_from_event(event)
    circle_id = _resolve_circle_id(body.get("circleId"), principal)
    require(principal, circle_id, roles=("owner",))
    plan = _load(circle_id, params["planId"])
    if plan is None:
        return respond(404, {"code": "not_found", "message": "plan not found"})
    if plan.status == "active":
        return respond(409, {"code": "conflict", "message": "plan already active"})

    errors = can_activate(plan)
    if errors:
        return respond(422, {"code": "validation_failed", "message": "; ".join(errors)})

    doses = build_doses(plan, now_ist().date(), days=30)
    table = _ddb.Table(TABLE)
    for dose in doses:
        try:
            table.put_item(
                Item={"PK": "CIRCLE#%s" % circle_id,
                      "SK": "DOSE#%s#%s" % (dose.date, dose.slot),
                      "doseId": dose.doseId, "date": dose.date,
                      "slot": dose.slot, "status": "pending",
                      "medicineLineIds": dose.medicineLineIds},
                ConditionExpression="attribute_not_exists(PK)")
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
    plan.status = "active"
    _save(plan)
    create_dose_schedules(plan, doses)
    if doses:
        first = min(doses, key=lambda d: (d.date, d.slot))
        hhmm = plan.slotTimes.get(first.slot, "08:00")
        local = datetime.fromisoformat("%sT%s:00" % (first.date, hhmm)).replace(tzinfo=IST)
        first_at = local.astimezone(timezone.utc).isoformat()
    else:
        first_at = None
    return respond(200, {"planId": plan.planId, "status": "active",
                         "dosesCreated": len(doses), "firstDoseAt": first_at})
