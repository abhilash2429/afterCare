import json
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from api.auth import principal_from_event, require
from api.common import REGION, TABLE, now_ist
from api.doses import build_doses
from api.handler import respond, route
from api.models import Dose, Plan
from api.schedules import create_dose_schedules, delete_dose_schedule, dose_at
from api.validate import can_activate, validate_edit

_ddb = boto3.resource("dynamodb", region_name=REGION)
DOSE_TTL = 90 * 24 * 3600


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
    line_ids += [lid for lid in orig_by if lid not in edit_by]
    now = datetime.now(timezone.utc)
    item = {
        "PK": "CIRCLE#%s" % circle_id,
        "SK": "AUDIT#%s#%s" % (now.isoformat(), edited.planId),
        "by": principal.get("sub"),
        "lineIds": line_ids,
        "before": [orig_by[lid] for lid in line_ids if lid in orig_by],
        "after": [edit_by[lid] for lid in line_ids if lid in edit_by],
        "expiresAt": int(time.time()) + 30 * 24 * 3600,
    }
    _ddb.Table(TABLE).put_item(
        Item=json.loads(json.dumps(item, default=str), parse_float=str))


def _retire_pending_doses(plan, now):
    """A new plan replaces the circle's active one: its still-pending doses from today on
    and their reminder schedules go, so the new plan's doses can take those slots."""
    table = _ddb.Table(TABLE)
    items, start = [], None
    while True:
        kw = {"KeyConditionExpression": "PK = :p AND SK BETWEEN :s AND :e",
              "ExpressionAttributeValues": {":p": "CIRCLE#%s" % plan.circleId,
                                            ":s": "DOSE#%s" % now.date().isoformat(),
                                            ":e": "DOSE#9999"}}
        if start:
            kw["ExclusiveStartKey"] = start
        res = table.query(**kw)
        items.extend(res.get("Items", []))
        start = res.get("LastEvaluatedKey")
        if not start:
            break
    for item in items:
        if item.get("status") != "pending":
            continue
        try:
            table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]},
                              ConditionExpression="#s = :pending",
                              ExpressionAttributeNames={"#s": "status"},
                              ExpressionAttributeValues={":pending": "pending"})
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
            continue
        delete_dose_schedule(plan, Dose(doseId=item.get("doseId", ""),
                                        date=item["date"], slot=item["slot"]))


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
    # Doses and reminder schedules are cut from the plan at activation; editing it
    # afterwards would silently diverge from them.
    if original.status != "draft":
        return respond(409, {"code": "conflict", "message": "plan is %s and can no longer be edited"
                             % original.status})

    edited = Plan.from_dict({**original.to_dict(),
                             "medicines": body.get("medicines", original.to_dict()["medicines"]),
                             "language": body.get("language", original.language),
                             "slotTimes": body.get("slotTimes", original.slotTimes)})
    # The confidence floor judges the model's reading; once the owner confirms a flagged
    # line it is human-verified, else a low-confidence line could never be activated.
    flagged = {m.lineId for m in original.medicines if m.needsConfirmation}
    for m in edited.medicines:
        if m.lineId in flagged and not m.needsConfirmation:
            m.confidence = 1.0
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
    if plan.status != "draft":
        return respond(409, {"code": "conflict", "message": "plan is already %s" % plan.status})

    errors = can_activate(plan)
    if errors:
        return respond(422, {"code": "validation_failed", "message": "; ".join(errors)})

    now = now_ist()
    # A slot whose time has already passed today is not a dose: it would fire a
    # reminder in the past and count as missed before anyone could give it.
    doses = [d for d in build_doses(plan, now.date(), days=30) if dose_at(plan, d) > now]
    if not doses:
        return respond(422, {"code": "validation_failed",
                             "message": "plan has no scheduled doses (every line is as-needed)"})
    table = _ddb.Table(TABLE)
    meta = table.get_item(Key={"PK": "CIRCLE#%s" % circle_id, "SK": "META"}).get("Item") or {}
    previous = meta.get("activePlanId")
    if previous and previous != plan.planId:
        _retire_pending_doses(plan, now)
    created = 0
    for dose in doses:
        try:
            table.put_item(
                Item={"PK": "CIRCLE#%s" % circle_id,
                      "SK": "DOSE#%s#%s" % (dose.date, dose.slot),
                      "doseId": dose.doseId, "date": dose.date,
                      "slot": dose.slot, "status": "pending",
                      "medicineLineIds": dose.medicineLineIds, "planId": plan.planId,
                      "expiresAt": int(dose_at(plan, dose).timestamp()) + DOSE_TTL},
                ConditionExpression="attribute_not_exists(PK)")
            created += 1
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise
    # Schedules before the status flip: if the scheduler fails, the plan stays draft and
    # activate can be retried (dose writes above are idempotent).
    create_dose_schedules(plan, doses)
    plan.status = "active"
    _save(plan)
    table.update_item(
        Key={"PK": "CIRCLE#%s" % plan.circleId, "SK": "META"},
        UpdateExpression="SET activePlanId = :p", ExpressionAttributeValues={":p": plan.planId})
    if previous and previous != plan.planId:
        old = _load(circle_id, previous)
        if old is not None:
            old.status = "archived"
            _save(old)
    first_at = min((dose_at(plan, d) for d in doses), default=None)
    first_at = first_at.isoformat() if first_at else None
    return respond(200, {"planId": plan.planId, "status": "active",
                         "dosesCreated": created, "firstDoseAt": first_at})
