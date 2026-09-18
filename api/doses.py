import json
from datetime import timedelta
from urllib.parse import unquote

import boto3

from api.auth import principal_from_event, require
from api.common import REGION, TABLE, now_ist
from api.handler import respond, route
from api.models import SLOTS, Dose

_ddb = boto3.resource("dynamodb", region_name=REGION)

DEFAULT_DAYS = 7


def build_doses(plan, start_date, days=7):
    doses = []
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        by_slot = {}
        for med in plan.medicines:
            if med.prn or not med.slots:
                continue
            limit = med.durationDays if med.durationDays is not None else DEFAULT_DAYS
            if offset >= limit:
                continue
            for slot in med.slots:
                by_slot.setdefault(slot, []).append(med.lineId)
        for slot in SLOTS:
            if slot in by_slot:
                doses.append(Dose(
                    doseId="%s#%s#%s" % (plan.circleId, day.isoformat(), slot),
                    date=day.isoformat(), slot=slot,
                    medicineLineIds=sorted(by_slot[slot])))
    return doses


DOSE_FIELDS = ("doseId", "date", "slot", "status", "givenAt", "givenBy",
               "medicineLineIds")


def _dose_shape(item):
    shape = {k: item.get(k) for k in DOSE_FIELDS}
    if shape["givenAt"] is None:
        shape["givenAt"] = None
    if shape["givenBy"] is None:
        shape["givenBy"] = None
    if shape["medicineLineIds"] is None:
        shape["medicineLineIds"] = []
    return json.loads(json.dumps(shape, default=str))


def _parse_dose_id(raw):
    """Path params arrive URL-encoded (%23 for #); handler does not decode (A6)."""
    dose_id = unquote(raw)
    circle_id, date, slot = dose_id.rsplit("#", 2)
    if not circle_id or not date or not slot:
        raise ValueError("invalid doseId")
    return dose_id, circle_id, date, slot


def _resolve_circle_id(explicit, principal):
    circle_id = explicit or principal.get("circleId")
    if not circle_id:
        raise ValueError("circleId is required")
    return circle_id


@route("POST", "/doses/{doseId}/given")
def mark_given(event, params):
    dose_id, circle_id, date, slot = _parse_dose_id(params["doseId"])
    principal = require(principal_from_event(event), circle_id)
    table = _ddb.Table(TABLE)
    item = table.get_item(
        Key={"PK": "CIRCLE#%s" % circle_id,
             "SK": "DOSE#%s#%s" % (date, slot)}).get("Item")
    if item is None:
        return respond(404, {"code": "not_found", "message": "dose not found"})
    if item.get("status") == "given":
        return respond(200, _dose_shape(item))
    res = table.update_item(
        Key={"PK": "CIRCLE#%s" % circle_id, "SK": "DOSE#%s#%s" % (date, slot)},
        UpdateExpression="SET #s = :given, givenAt = :at, givenBy = :by",
        ConditionExpression="attribute_exists(PK)",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={":given": "given",
                                   ":at": now_ist().isoformat(),
                                   ":by": principal["sub"]},
        ReturnValues="ALL_NEW")
    return respond(200, _dose_shape(res["Attributes"]))


@route("GET", "/plans/{planId}/adherence")
def adherence(event, params):
    principal = principal_from_event(event)
    query = event.get("queryStringParameters") or {}
    circle_id = _resolve_circle_id(query.get("circleId"), principal)
    require(principal, circle_id)
    try:
        days = int(query.get("days", 7))
    except (TypeError, ValueError):
        raise ValueError("days must be an integer")
    if days < 1 or days > 30:
        raise ValueError("days must be between 1 and 30")
    today = now_ist().date()
    cutoff = (today - timedelta(days=days - 1)).isoformat()
    today_iso = today.isoformat()
    table = _ddb.Table(TABLE)
    items, start = [], None
    while True:
        kw = {"KeyConditionExpression": "PK = :p AND begins_with(SK, :s)",
              "ExpressionAttributeValues": {":p": "CIRCLE#%s" % circle_id,
                                            ":s": "DOSE#"}}
        if start:
            kw["ExclusiveStartKey"] = start
        res = table.query(**kw)
        items.extend(res.get("Items", []))
        start = res.get("LastEvaluatedKey")
        if not start:
            break
    window = [i for i in items
              if cutoff <= str(i.get("date", "")) <= today_iso]
    window.sort(key=lambda i: (str(i.get("date", "")),
                               SLOTS.index(i["slot"]) if i.get("slot") in SLOTS else -1),
                reverse=True)
    doses = [_dose_shape(i) for i in window]
    given = len([d for d in doses if d.get("status") == "given"])
    missed = len([d for d in doses if d.get("status") == "missed"])
    scored = given + missed
    given_pct = round(100.0 * given / scored, 1) if scored else 0.0
    return respond(200, {"doses": doses, "givenPct": given_pct})
