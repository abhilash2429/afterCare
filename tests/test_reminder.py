"""Task 12: reminder Lambda, mark-given, adherence (amendments A1-A8)."""
import json
import re
from datetime import datetime
from urllib.parse import quote

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

import api.auth as auth
from api.common import IST
from api.handler import lambda_handler
from api.reminder import decide

SECRET = "test-secret-that-is-at-least-32-bytes-long"
CTX_ARN = "arn:aws:lambda:ap-south-1:123456789012:function:reminder"


class Ctx:
    invoked_function_arn = CTX_ARN


class FakeScheduler:
    class exceptions:
        class ConflictException(Exception):
            pass

    def __init__(self):
        self.calls = []

    def create_schedule(self, **kw):
        self.calls.append(kw)


@pytest.fixture
def table(monkeypatch):
    for k, v in {"AWS_ACCESS_KEY_ID": "x", "AWS_SECRET_ACCESS_KEY": "x",
                 "AWS_DEFAULT_REGION": "ap-south-1"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("REMINDER_SELF_ARN", raising=False)
    monkeypatch.setenv("SCHEDULER_ROLE_ARN",
                       "arn:aws:iam::123456789012:role/aftercare-scheduler")
    monkeypatch.setattr(auth, "_secret", lambda: SECRET)
    with mock_aws():
        t = boto3.resource("dynamodb", region_name="ap-south-1").create_table(
            TableName="aftercare", BillingMode="PAY_PER_REQUEST",
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"},
                       {"AttributeName": "SK", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"},
                                  {"AttributeName": "SK", "AttributeType": "S"}])
        monkeypatch.setattr(auth, "_table_cache", t)
        t.put_item(Item={"PK": "CIRCLE#ci_1", "SK": "PLAN#pl_1", "planId": "pl_1"})
        import api.reminder as reminder
        import api.dose_routes as dosesmod
        monkeypatch.setattr(reminder, "_ddb",
                            boto3.resource("dynamodb", region_name="ap-south-1"))
        monkeypatch.setattr(dosesmod, "_ddb",
                            boto3.resource("dynamodb", region_name="ap-south-1"))
        yield t


def _seed_dose(table, circle="ci_1", date="2026-09-20", slot="morning",
               status="pending", lines=None):
    table.put_item(Item={
        "PK": "CIRCLE#%s" % circle, "SK": "DOSE#%s#%s" % (date, slot),
        "doseId": "%s#%s#%s" % (circle, date, slot),
        "date": date, "slot": slot, "status": status,
        "medicineLineIds": ["m1"] if lines is None else lines})


def _stub_doses_auth(monkeypatch, sub="u-care", circle="ci_1", role="caregiver"):
    import api.dose_routes as dosesmod
    principal = {"sub": sub, "circleId": circle, "role": role}
    monkeypatch.setattr(dosesmod, "principal_from_event", lambda event: principal)
    monkeypatch.setattr(dosesmod, "require",
                        lambda p, cid, roles=("owner", "caregiver"): p)
    return principal


def _event(method, path, body=None, query=None, token=None, raw_body=None):
    e = {"requestContext": {"http": {"method": method, "path": path}},
         "headers": {}, "queryStringParameters": query}
    if token:
        e["headers"]["authorization"] = "Bearer %s" % token
    if raw_body is not None:
        e["body"] = raw_body
    elif body is not None:
        e["body"] = json.dumps(body)
    return e


# --- brief decide tests ---

def test_remind_phase_sends_a_reminder_and_schedules_a_check():
    assert decide({"phase": "remind"}, dose_status="pending") == ("remind", True)


def test_check_phase_escalates_when_still_pending():
    assert decide({"phase": "check"}, dose_status="pending") == ("escalate", False)


def test_check_phase_does_nothing_when_given():
    assert decide({"phase": "check"}, dose_status="given") == ("none", False)


def test_remind_phase_skips_an_already_given_dose():
    assert decide({"phase": "remind"}, dose_status="given") == ("none", False)


# --- A2: only pending reminds/escalates; missing dose -> none ---

def test_remind_on_missed_dose_does_nothing(table, monkeypatch):
    import api.reminder as reminder
    _seed_dose(table, status="missed")
    monkeypatch.setattr(reminder, "send_reminder",
                        lambda *a: pytest.fail("must not remind"))
    sched = FakeScheduler()
    monkeypatch.setattr(reminder, "_scheduler", sched)
    res = reminder.lambda_handler(
        {"circleId": "ci_1", "doseId": "ci_1#2026-09-20#morning", "phase": "remind"}, Ctx())
    assert res == {"action": "none"}
    assert sched.calls == []


def test_check_on_missed_dose_does_nothing(table, monkeypatch):
    import api.reminder as reminder
    _seed_dose(table, status="missed")
    monkeypatch.setattr(reminder, "send_escalation",
                        lambda *a: pytest.fail("must not escalate"))
    res = reminder.lambda_handler(
        {"circleId": "ci_1", "doseId": "ci_1#2026-09-20#morning", "phase": "check"}, Ctx())
    assert res == {"action": "none"}


def test_missing_dose_returns_none_without_exception(table, monkeypatch):
    import api.reminder as reminder
    monkeypatch.setattr(reminder, "send_reminder",
                        lambda *a: pytest.fail("must not remind"))
    monkeypatch.setattr(reminder, "send_escalation",
                        lambda *a: pytest.fail("must not escalate"))
    sched = FakeScheduler()
    monkeypatch.setattr(reminder, "_scheduler", sched)
    for phase in ("remind", "check"):
        res = reminder.lambda_handler(
            {"circleId": "ci_1", "doseId": "ci_1#2026-09-20#morning",
             "phase": phase}, Ctx())
        assert res == {"action": "none"}
    assert sched.calls == []


def test_given_dose_never_reminds_or_schedules(table, monkeypatch):
    import api.reminder as reminder
    _seed_dose(table, status="given")
    monkeypatch.setattr(reminder, "send_reminder",
                        lambda *a: pytest.fail("must not remind"))
    sched = FakeScheduler()
    monkeypatch.setattr(reminder, "_scheduler", sched)
    res = reminder.lambda_handler(
        {"circleId": "ci_1", "doseId": "ci_1#2026-09-20#morning", "phase": "remind"}, Ctx())
    assert res == {"action": "none"}
    assert sched.calls == []


# --- remind creates a check schedule (A3 target, A4 name/group/minutes) ---

def test_remind_sends_and_schedules_check(table, monkeypatch):
    import api.reminder as reminder
    _seed_dose(table)
    table.put_item(Item={"PK": "CIRCLE#ci_1", "SK": "META", "escalationMinutes": 45})
    sent = []
    monkeypatch.setattr(reminder, "send_reminder",
                        lambda cid, dose: sent.append((cid, dose["doseId"])))
    sched = FakeScheduler()
    monkeypatch.setattr(reminder, "_scheduler", sched)
    res = reminder.lambda_handler(
        {"circleId": "ci_1", "doseId": "ci_1#2026-09-20#morning", "phase": "remind"}, Ctx())
    assert res == {"action": "remind"}
    assert sent == [("ci_1", "ci_1#2026-09-20#morning")]
    assert len(sched.calls) == 1
    call = sched.calls[0]
    assert call["GroupName"] == "aftercare"
    assert call["Target"]["Arn"] == CTX_ARN  # A3: context ARN, not env
    assert call["Target"]["RoleArn"].endswith("aftercare-scheduler")
    assert json.loads(call["Target"]["Input"])["phase"] == "check"
    assert call["ScheduleExpressionTimezone"] == "Asia/Kolkata"


def test_check_schedule_name_is_sanitised_check_prefix(table, monkeypatch):
    import api.reminder as reminder
    _seed_dose(table, circle="ci evil/id", date="2026-09-20", slot="morning")
    monkeypatch.setattr(reminder, "send_reminder", lambda *a: None)
    sched = FakeScheduler()
    monkeypatch.setattr(reminder, "_scheduler", sched)
    res = reminder.lambda_handler(
        {"circleId": "ci evil/id", "doseId": "ci evil/id#2026-09-20#morning",
         "phase": "remind"}, Ctx())
    assert res == {"action": "remind"}
    name = sched.calls[0]["Name"]
    assert name.startswith("check-")
    assert len(name) <= 64
    assert re.fullmatch(r"[0-9a-zA-Z-_.]+", name)


def test_check_schedule_conflict_is_ignored(table, monkeypatch):
    import api.reminder as reminder
    _seed_dose(table)
    monkeypatch.setattr(reminder, "send_reminder", lambda *a: None)

    class ConflictScheduler(FakeScheduler):
        def create_schedule(self, **kw):
            self.calls.append(kw)
            raise FakeScheduler.exceptions.ConflictException({}, "create")

    monkeypatch.setattr(reminder, "_scheduler", ConflictScheduler())
    res = reminder.lambda_handler(
        {"circleId": "ci_1", "doseId": "ci_1#2026-09-20#morning", "phase": "remind"}, Ctx())
    assert res == {"action": "remind"}


def test_escalation_minutes_default_and_clamped(monkeypatch):
    import api.reminder as reminder
    assert reminder.escalation_minutes({}) == 30
    assert reminder.escalation_minutes({"escalationMinutes": 2}) == 5
    assert reminder.escalation_minutes({"escalationMinutes": 999}) == 240
    assert reminder.escalation_minutes({"escalationMinutes": 45}) == 45


# --- check on pending -> missed + escalation; race -> none (A2) ---

def test_check_on_pending_marks_missed_and_escalates(table, monkeypatch):
    import api.reminder as reminder
    _seed_dose(table)
    sent = []
    monkeypatch.setattr(reminder, "send_escalation",
                        lambda cid, dose: sent.append(cid))
    res = reminder.lambda_handler(
        {"circleId": "ci_1", "doseId": "ci_1#2026-09-20#morning", "phase": "check"}, Ctx())
    assert res == {"action": "escalate"}
    assert sent == ["ci_1"]
    item = table.get_item(Key={"PK": "CIRCLE#ci_1",
                               "SK": "DOSE#2026-09-20#morning"})["Item"]
    assert item["status"] == "missed"


def test_check_after_given_does_nothing(table, monkeypatch):
    import api.reminder as reminder
    _seed_dose(table, status="given")
    monkeypatch.setattr(reminder, "send_escalation",
                        lambda *a: pytest.fail("must not escalate"))
    res = reminder.lambda_handler(
        {"circleId": "ci_1", "doseId": "ci_1#2026-09-20#morning", "phase": "check"}, Ctx())
    assert res == {"action": "none"}


def test_check_loses_race_to_given_without_escalation(table, monkeypatch):
    import api.reminder as reminder
    _seed_dose(table)
    monkeypatch.setattr(reminder, "send_escalation",
                        lambda *a: pytest.fail("must not escalate"))
    real_table = reminder._ddb.Table("aftercare")
    orig_get = real_table.get_item

    def flaky_update(**kw):
        raise ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException", "Message": "race"}},
            "UpdateItem")

    class FakeTable:
        def get_item(self, **kw):
            return orig_get(**kw)

        def update_item(self, **kw):
            return flaky_update(**kw)

    class FakeDDB:
        def Table(self, name):
            assert name == "aftercare"
            return FakeTable()

    monkeypatch.setattr(reminder, "_ddb", FakeDDB())
    res = reminder.lambda_handler(
        {"circleId": "ci_1", "doseId": "ci_1#2026-09-20#morning", "phase": "check"}, Ctx())
    assert res == {"action": "none"}


# --- A6: POST /doses/{doseId}/given (URL-encoded) ---

def test_given_route_decodes_url_encoded_dose_id(table, monkeypatch):
    _stub_doses_auth(monkeypatch, sub="u-care")
    _seed_dose(table)
    import api.dose_routes as dosesmod
    monkeypatch.setattr(dosesmod, "now_ist",
                        lambda: datetime(2026, 9, 20, 9, 0, tzinfo=IST))
    enc = quote("ci_1#2026-09-20#morning", safe="")
    assert "%23" in enc
    res = lambda_handler(_event("POST", "/doses/%s/given" % enc, {}), None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["doseId"] == "ci_1#2026-09-20#morning"
    assert body["status"] == "given"
    assert body["givenBy"] == "u-care"
    assert body["givenAt"]
    assert body["medicineLineIds"] == ["m1"]
    for key in ("doseId", "date", "slot", "status", "medicineLineIds"):
        assert key in body


def test_given_is_idempotent(table, monkeypatch):
    _stub_doses_auth(monkeypatch, sub="u-care")
    _seed_dose(table, status="given")
    table.update_item(Key={"PK": "CIRCLE#ci_1", "SK": "DOSE#2026-09-20#morning"},
                      UpdateExpression="SET givenAt = :a, givenBy = :b",
                      ExpressionAttributeValues={":a": "2026-09-20T09:00:00+05:30",
                                                 ":b": "u-care"})
    enc = quote("ci_1#2026-09-20#morning", safe="")
    res = lambda_handler(_event("POST", "/doses/%s/given" % enc, {}), None)
    assert res["statusCode"] == 200
    assert json.loads(res["body"])["status"] == "given"


def test_given_allows_late_mark_on_missed_dose(table, monkeypatch):
    _stub_doses_auth(monkeypatch, sub="u-care")
    _seed_dose(table, status="missed")
    enc = quote("ci_1#2026-09-20#morning", safe="")
    res = lambda_handler(_event("POST", "/doses/%s/given" % enc, {}), None)
    assert res["statusCode"] == 200
    assert json.loads(res["body"])["status"] == "given"


def test_given_unknown_dose_is_404(table, monkeypatch):
    _stub_doses_auth(monkeypatch)
    enc = quote("ci_1#2026-09-20#morning", safe="")
    res = lambda_handler(_event("POST", "/doses/%s/given" % enc, {}), None)
    assert res["statusCode"] == 404


def test_given_with_bad_dose_id_is_422(table, monkeypatch):
    _stub_doses_auth(monkeypatch)
    res = lambda_handler(_event("POST", "/doses/not-a-dose/given", {}), None)
    assert res["statusCode"] == 422


def test_given_wrong_circle_is_403(table):
    token = auth.issue_circle_token("ci_OTHER", "caregiver")
    enc = quote("ci_1#2026-09-20#morning", safe="")
    res = lambda_handler(_event("POST", "/doses/%s/given" % enc, {}, token=token), None)
    assert res["statusCode"] == 403


def test_given_needs_a_token(table):
    enc = quote("ci_1#2026-09-20#morning", safe="")
    res = lambda_handler(_event("POST", "/doses/%s/given" % enc, {}), None)
    assert res["statusCode"] == 401


# --- A7: GET /plans/{planId}/adherence ---

def _seed_adherence(table):
    _seed_dose(table, date="2026-09-20", slot="morning", status="given")
    _seed_dose(table, date="2026-09-20", slot="night", status="missed")
    _seed_dose(table, date="2026-09-19", slot="morning", status="given")
    _seed_dose(table, date="2026-09-19", slot="night", status="pending")
    _seed_dose(table, date="2026-09-10", slot="morning", status="given")  # old
    _seed_dose(table, date="2026-09-21", slot="morning", status="pending")  # future


def test_adherence_math_excludes_pending(table, monkeypatch):
    import api.dose_routes as dosesmod
    _stub_doses_auth(monkeypatch)
    _seed_adherence(table)
    monkeypatch.setattr(dosesmod, "now_ist",
                        lambda: datetime(2026, 9, 20, 12, 0, tzinfo=IST))
    res = lambda_handler(
        _event("GET", "/plans/pl_1/adherence", query={"circleId": "ci_1"}), None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    # window days=7 covers 09-14..09-20: given=2, missed=1 -> 66.7
    assert body["givenPct"] == 66.7
    dates = [d["date"] for d in body["doses"]]
    assert dates == sorted(dates, reverse=True)
    assert "2026-09-21" not in dates  # future excluded
    assert "2026-09-10" not in dates  # outside window excluded
    assert all(d["date"] <= "2026-09-20" for d in body["doses"])


def test_adherence_no_scored_doses_is_zero(table, monkeypatch):
    import api.dose_routes as dosesmod
    _stub_doses_auth(monkeypatch)
    _seed_dose(table, date="2026-09-20", slot="morning", status="pending")
    monkeypatch.setattr(dosesmod, "now_ist",
                        lambda: datetime(2026, 9, 20, 12, 0, tzinfo=IST))
    res = lambda_handler(
        _event("GET", "/plans/pl_1/adherence", query={"circleId": "ci_1"}), None)
    assert json.loads(res["body"])["givenPct"] == 0.0


def test_adherence_days_over_30_is_422(table, monkeypatch):
    _stub_doses_auth(monkeypatch)
    res = lambda_handler(
        _event("GET", "/plans/pl_1/adherence",
               query={"circleId": "ci_1", "days": "31"}), None)
    assert res["statusCode"] == 422


def test_adherence_caregiver_token_supplies_circle(table, monkeypatch):
    import api.dose_routes as dosesmod
    token = auth.issue_circle_token("ci_1", "caregiver")
    _seed_dose(table, status="given")
    monkeypatch.setattr(dosesmod, "now_ist",
                        lambda: datetime(2026, 9, 20, 12, 0, tzinfo=IST))
    res = lambda_handler(_event("GET", "/plans/pl_1/adherence", token=token), None)
    assert res["statusCode"] == 200
    assert json.loads(res["body"])["givenPct"] == 100.0


# --- A5: infra guard ---

def test_infra_gives_reminder_scheduler_perms():
    import pathlib
    src = pathlib.Path("infra/aftercare_stack.py").read_text()
    assert "SCHEDULER_ROLE_ARN" in src
    assert "scheduler:CreateSchedule" in src
    assert "iam:PassRole" in src
    assert "scheduler.amazonaws.com" in src
    assert "schedule/aftercare/*" in src


def test_adherence_unknown_plan_is_404(table, monkeypatch):
    _stub_doses_auth(monkeypatch)
    _seed_adherence(table)
    res = lambda_handler(
        _event("GET", "/plans/pl_nope/adherence", query={"circleId": "ci_1"}), None)
    assert res["statusCode"] == 404


def test_dose_from_another_circle_is_ignored(table, monkeypatch):
    import api.reminder as reminder
    _seed_dose(table, date="2026-09-20", slot="morning", status="pending")
    sent = []
    monkeypatch.setattr(reminder, "send_reminder", lambda *a: sent.append(a))
    out = reminder.lambda_handler({"circleId": "ci_other", "doseId": "ci_1#2026-09-20#morning",
                                   "phase": "remind"}, None)
    assert out == {"action": "none"} and sent == []
