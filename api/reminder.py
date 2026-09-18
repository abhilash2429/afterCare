import json
import logging
import os
from datetime import timedelta

import boto3
from botocore.exceptions import ClientError

import api.schedules as schedules
from api.common import REGION, TABLE, now_ist, redact
from api.notify import send_escalation, send_reminder

log = logging.getLogger()

_ddb = boto3.resource("dynamodb", region_name=REGION)
_scheduler = boto3.client("scheduler", region_name=REGION)

DEFAULT_ESCALATION_MINUTES = 30
MIN_ESCALATION_MINUTES = 5
MAX_ESCALATION_MINUTES = 240


def decide(event, dose_status):
    """Pure decision: (action, needs_followup_schedule)."""
    if dose_status != "pending":
        return "none", False
    phase = event.get("phase")
    if phase == "remind":
        return "remind", True
    if phase == "check":
        return "escalate", False
    return "none", False


def parse_dose_id(dose_id):
    """Split "<circleId>#<yyyy-mm-dd>#<slot>" (A1)."""
    circle_id, date, slot = dose_id.rsplit("#", 2)
    if not circle_id or not date or not slot:
        raise ValueError("invalid doseId")
    return circle_id, date, slot


def check_schedule_name(dose_id):
    """Same sanitising rule as api/schedules.py (A4), prefix "check-"."""
    return schedules._UNSAFE.sub("-", "check-%s" % dose_id)[:64]


def escalation_minutes(circle):
    """escalationMinutes from CIRCLE META, default 30, clamped 5..240 (A4)."""
    try:
        minutes = int(circle.get("escalationMinutes", DEFAULT_ESCALATION_MINUTES))
    except (TypeError, ValueError):
        minutes = DEFAULT_ESCALATION_MINUTES
    return max(MIN_ESCALATION_MINUTES, min(MAX_ESCALATION_MINUTES, minutes))


def _target_arn(context):
    arn = getattr(context, "invoked_function_arn", None)
    if arn is None and isinstance(context, dict):
        arn = context.get("invoked_function_arn")
    if not arn:
        raise ValueError("context.invoked_function_arn is required")
    return arn


def _get_dose(circle_id, date, slot):
    return _ddb.Table(TABLE).get_item(
        Key={"PK": "CIRCLE#%s" % circle_id,
             "SK": "DOSE#%s#%s" % (date, slot)}).get("Item")


def _schedule_check(event, circle_id, dose_id, context):
    circle = _ddb.Table(TABLE).get_item(
        Key={"PK": "CIRCLE#%s" % circle_id, "SK": "META"}).get("Item") or {}
    minutes = escalation_minutes(circle)
    at = (now_ist() + timedelta(minutes=minutes)).strftime("at(%Y-%m-%dT%H:%M:%S)")
    try:
        _scheduler.create_schedule(
            Name=check_schedule_name(dose_id), GroupName=schedules.GROUP,
            ScheduleExpression=at,
            ScheduleExpressionTimezone="Asia/Kolkata",
            FlexibleTimeWindow={"Mode": "OFF"}, ActionAfterCompletion="DELETE",
            Target={"Arn": _target_arn(context),
                    "RoleArn": os.environ["SCHEDULER_ROLE_ARN"],
                    "Input": json.dumps({**event, "phase": "check"})})
    except _scheduler.exceptions.ConflictException:
        log.info("check schedule already exists dose=%s", redact(dose_id))


def lambda_handler(event, context):
    circle_id, dose_id = event.get("circleId"), event.get("doseId")
    if not circle_id or not dose_id:
        return {"action": "none"}
    try:
        _cid, date, slot = parse_dose_id(dose_id)
    except ValueError:
        log.warning("bad doseId dose=%s", redact(dose_id))
        return {"action": "none"}
    dose = _get_dose(circle_id, date, slot)
    if dose is None:  # A2: missing dose item -> none, no exception
        log.info("dose not found circle=%s dose=%s",
                 redact(circle_id), redact(dose_id))
        return {"action": "none"}
    action, follow_up = decide(event, dose.get("status", "pending"))
    if action == "none":
        return {"action": "none"}

    if action == "remind":
        send_reminder(circle_id, dose)
    elif action == "escalate":
        try:
            _ddb.Table(TABLE).update_item(
                Key={"PK": "CIRCLE#%s" % circle_id,
                     "SK": "DOSE#%s#%s" % (date, slot)},
                UpdateExpression="SET #s = :missed",
                ConditionExpression="#s = :pending",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":missed": "missed", ":pending": "pending"})
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                log.info("dose given before check circle=%s dose=%s",
                         redact(circle_id), redact(dose_id))
                return {"action": "none"}
            raise
        send_escalation(circle_id, {**dose, "status": "missed"})

    if follow_up:
        _schedule_check(event, circle_id, dose_id, context)
    return {"action": action}
