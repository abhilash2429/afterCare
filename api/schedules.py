import json
import os
import re
from datetime import datetime, timezone

import boto3

from api.common import IST, REGION

_scheduler = boto3.client("scheduler", region_name=REGION)
GROUP = "aftercare"
MAX_SCHEDULES = 200  # demo guard: 30 days x 4 slots stays well under this

_UNSAFE = re.compile(r"[^0-9a-zA-Z-_.]")


def schedule_name_for_dose(plan, dose):
    raw = "dose-%s-%s-%s" % (plan.circleId, dose.date, dose.slot)
    return _UNSAFE.sub("-", raw)[:64]


def dose_at(plan, dose):
    """UTC instant of a dose: its date at the plan's IST slot time."""
    hhmm = plan.slotTimes.get(dose.slot, "08:00")
    local = datetime.fromisoformat("%sT%s:00" % (dose.date, hhmm)).replace(tzinfo=IST)
    return local.astimezone(timezone.utc)


def create_dose_schedules(plan, doses):
    target_arn = os.environ["REMINDER_ARN"]
    role_arn = os.environ["SCHEDULER_ROLE_ARN"]
    created = 0
    for dose in doses[:MAX_SCHEDULES]:
        at = dose_at(plan, dose).strftime("at(%Y-%m-%dT%H:%M:%S)")
        try:
            _scheduler.create_schedule(
                Name=schedule_name_for_dose(plan, dose),
                GroupName=GROUP,
                ScheduleExpression=at,
                ScheduleExpressionTimezone="UTC",
                FlexibleTimeWindow={"Mode": "OFF"},
                ActionAfterCompletion="DELETE",
                Target={"Arn": target_arn, "RoleArn": role_arn,
                        "Input": json.dumps({"doseId": dose.doseId,
                                             "circleId": plan.circleId,
                                             "planId": plan.planId,
                                             "phase": "remind"})})
            created += 1
        except _scheduler.exceptions.ConflictException:
            pass
    return created
