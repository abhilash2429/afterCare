import json

import boto3
import pytest
import pywebpush
from moto import mock_aws

import api.auth as auth
import api.notify as notify
from api.handler import lambda_handler
from api.notify import channels_for

SUB = {"endpoint": "https://push.example.com/x", "keys": {"p256dh": "p", "auth": "a"}}


@pytest.fixture
def table(monkeypatch):
    for k, v in {"AWS_ACCESS_KEY_ID": "x", "AWS_SECRET_ACCESS_KEY": "x",
                 "AWS_DEFAULT_REGION": "ap-south-1"}.items():
        monkeypatch.setenv(k, v)
    with mock_aws():
        t = boto3.resource("dynamodb", region_name="ap-south-1").create_table(
            TableName="aftercare", BillingMode="PAY_PER_REQUEST",
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"},
                       {"AttributeName": "SK", "KeyType": "RANGE"}],
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"},
                                  {"AttributeName": "SK", "AttributeType": "S"}])
        monkeypatch.setattr(auth, "_table_cache", t)
        yield t


def _event(method, path, body=None):
    e = {"requestContext": {"http": {"method": method, "path": path}}, "headers": {}}
    if body is not None:
        e["body"] = json.dumps(body)
    return e


def _stub_principal(monkeypatch, sub="u1", circle_id="ci_1", role="owner"):
    principal = {"sub": sub, "circleId": None, "role": role}
    monkeypatch.setattr(notify, "principal_from_event", lambda event: principal)
    monkeypatch.setattr(notify, "require", lambda p, cid, roles=("owner", "caregiver"): p)
    return principal


# channels_for


def test_caregiver_with_push_gets_push_only():
    assert channels_for({"role": "caregiver", "pushSubscription": {"endpoint": "x"}}) == ["push"]


def test_owner_gets_whatsapp_then_email(monkeypatch):
    monkeypatch.setenv("WHATSAPP_ENABLED", "true")
    member = {"role": "owner", "whatsappNumber": "+919876543210", "email": "a@b.com"}
    assert channels_for(member) == ["whatsapp", "email"]


def test_owner_without_whatsapp_falls_back_to_email():
    assert channels_for({"role": "owner", "email": "a@b.com"}) == ["email"]


def test_whatsapp_flag_off_by_default_falls_back_to_email(monkeypatch):
    monkeypatch.delenv("WHATSAPP_ENABLED", raising=False)
    member = {"role": "owner", "whatsappNumber": "+919876543210", "email": "a@b.com"}
    assert channels_for(member) == ["email"]


def test_member_with_nothing_gets_no_channels():
    assert channels_for({"role": "owner"}) == []


# POST /circles/{circleId}/push


def test_register_push_stores_subscription_on_caller_member(table, monkeypatch):
    _stub_principal(monkeypatch, sub="u1", circle_id="ci_1")
    table.put_item(Item={"PK": "CIRCLE#ci_1", "SK": "MEMBER#u1", "role": "owner"})
    res = lambda_handler(_event("POST", "/circles/ci_1/push", {"subscription": SUB}), None)
    assert res.get("statusCode") == 204
    item = table.get_item(Key={"PK": "CIRCLE#ci_1", "SK": "MEMBER#u1"})["Item"]
    assert item["pushSubscription"] == SUB


@pytest.mark.parametrize("body", [
    {},
    {"subscription": {}},
    {"subscription": {"endpoint": "http://not-https.example.com", "keys": SUB["keys"]}},
    {"subscription": {"endpoint": SUB["endpoint"], "keys": {"p256dh": "p"}}},
    {"subscription": {"endpoint": SUB["endpoint"], "keys": {}}},
])
def test_register_push_rejects_bad_shape(table, monkeypatch, body):
    _stub_principal(monkeypatch)
    res = lambda_handler(_event("POST", "/circles/ci_1/push", body), None)
    assert res["statusCode"] == 422


# dead Web Push subscriptions


class _FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.reason = "Gone"
        self.text = "gone"


def test_dead_push_subscription_is_removed_not_retried(table, monkeypatch):
    monkeypatch.setattr(notify, "_vapid_private_key", lambda: "priv")

    def raiser(**kwargs):
        raise pywebpush.WebPushException("gone", response=_FakeResponse(410))

    monkeypatch.setattr(pywebpush, "webpush", raiser)
    table.put_item(Item={"PK": "CIRCLE#ci_1", "SK": "MEMBER#u1", "role": "caregiver",
                         "pushSubscription": SUB})
    member = table.get_item(Key={"PK": "CIRCLE#ci_1", "SK": "MEMBER#u1"})["Item"]

    with pytest.raises(notify.DeadSubscription):
        notify._push(member, "t", "b")

    after = table.get_item(Key={"PK": "CIRCLE#ci_1", "SK": "MEMBER#u1"})["Item"]
    assert "pushSubscription" not in after


def test_non_dead_push_error_is_not_swallowed(monkeypatch):
    monkeypatch.setattr(notify, "_vapid_private_key", lambda: "priv")

    def raiser(**kwargs):
        raise pywebpush.WebPushException("boom", response=_FakeResponse(500))

    monkeypatch.setattr(pywebpush, "webpush", raiser)
    with pytest.raises(pywebpush.WebPushException):
        notify._push({"pushSubscription": SUB}, "t", "b")


# message copy


def test_send_reminder_copy_has_no_medicine_name(table, monkeypatch):
    table.put_item(Item={"PK": "CIRCLE#ci_1", "SK": "META", "name": "Amma"})
    table.put_item(Item={"PK": "CIRCLE#ci_1", "SK": "MEMBER#u1", "role": "owner",
                         "email": "a@b.com"})
    calls = []
    monkeypatch.setattr(notify, "_email", lambda member, subject, body: calls.append((subject, body)))
    notify.send_reminder("ci_1", {"slot": "night", "medicineLineIds": ["med_amlodipine"]})
    assert calls == [("AfterCare reminder", "Night medicines for Amma are due")]
    assert "amlodipine" not in calls[0][1].lower()


def test_send_escalation_copy_is_fixed_and_generic(table, monkeypatch):
    table.put_item(Item={"PK": "CIRCLE#ci_1", "SK": "MEMBER#u1", "role": "owner",
                         "email": "a@b.com"})
    calls = []
    monkeypatch.setattr(notify, "_email", lambda member, subject, body: calls.append((subject, body)))
    notify.send_escalation("ci_1", {"slot": "night", "date": "2026-09-20"})
    assert calls == [("AfterCare alert", "A dose was missed. Please check.")]


# fan-out resilience


def test_one_failing_channel_falls_back_to_the_next(table, monkeypatch):
    table.put_item(Item={"PK": "CIRCLE#ci_1", "SK": "MEMBER#u1", "role": "owner",
                         "email": "a@b.com", "pushSubscription": SUB})
    monkeypatch.setattr(notify, "_push", lambda *a: (_ for _ in ()).throw(RuntimeError("down")))
    calls = []
    monkeypatch.setattr(notify, "_email", lambda member, subject, body: calls.append(body))
    notify.send_reminder("ci_1", {"slot": "morning"})
    assert calls  # email still ran after push failed


def test_one_members_failure_never_blocks_the_next_member(table, monkeypatch):
    table.put_item(Item={"PK": "CIRCLE#ci_1", "SK": "MEMBER#u1", "role": "owner",
                         "email": "a@b.com"})
    table.put_item(Item={"PK": "CIRCLE#ci_1", "SK": "MEMBER#u2", "role": "owner",
                         "email": "c@d.com"})

    def flaky(member, subject, body):
        if member["SK"] == "MEMBER#u1":
            raise RuntimeError("ses down")

    calls = []
    monkeypatch.setattr(notify, "_email", lambda member, subject, body: (
        flaky(member, subject, body), calls.append(member["SK"]))[1])
    notify.send_reminder("ci_1", {"slot": "morning"})
    assert calls == ["MEMBER#u2"]


def test_dead_push_falls_back_to_email(table, monkeypatch):
    table.put_item(Item={"PK": "CIRCLE#ci_1", "SK": "MEMBER#u1", "role": "owner",
                         "email": "a@b.com", "pushSubscription": SUB})

    def dead(member, title, body):
        raise notify.DeadSubscription()

    monkeypatch.setattr(notify, "_push", dead)
    calls = []
    monkeypatch.setattr(notify, "_email", lambda member, subject, body: calls.append(body))
    notify.send_reminder("ci_1", {"slot": "morning"})
    assert calls


def test_escalation_uses_every_channel(table, monkeypatch):
    table.put_item(Item={"PK": "CIRCLE#ci_1", "SK": "MEMBER#u1", "role": "owner",
                         "email": "a@b.com", "pushSubscription": SUB})
    sent = []
    monkeypatch.setattr(notify, "_push", lambda member, title, body: sent.append("push"))
    monkeypatch.setattr(notify, "_email", lambda member, subject, body: sent.append("email"))
    notify.send_escalation("ci_1", {"slot": "night"})
    assert sent == ["push", "email"]
    sent.clear()
    notify.send_reminder("ci_1", {"slot": "night"})
    assert sent == ["push"]
