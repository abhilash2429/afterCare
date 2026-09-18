import json
import logging
import os

import boto3

from api.auth import _table, principal_from_event, require
from api.common import REGION, redact
from api.handler import respond, route

log = logging.getLogger()

_clients = {}
_vapid_private_cache = None


def _client(name):
    if name not in _clients:
        _clients[name] = boto3.client(name, region_name=REGION)
    return _clients[name]


def _vapid_private_key():
    global _vapid_private_cache
    if _vapid_private_cache is None:
        _vapid_private_cache = _client("ssm").get_parameter(
            Name=os.environ["VAPID_PRIVATE_PARAM"], WithDecryption=True)["Parameter"]["Value"]
    return _vapid_private_cache


def channels_for(member):
    """Push first (works for any role), then WhatsApp/email for owners only.
    WhatsApp additionally needs the flag on (money rule: off by default)."""
    out = []
    if member.get("pushSubscription"):
        out.append("push")
    if member.get("role") == "owner":
        if os.environ.get("WHATSAPP_ENABLED") == "true" and member.get("whatsappNumber"):
            out.append("whatsapp")
        if member.get("email"):
            out.append("email")
    return out


def _members(circle_id):
    res = _table().query(
        KeyConditionExpression="PK = :p AND begins_with(SK, :s)",
        ExpressionAttributeValues={":p": "CIRCLE#%s" % circle_id, ":s": "MEMBER#"})
    return res.get("Items", [])


def _circle_name(circle_id):
    meta = _table().get_item(Key={"PK": "CIRCLE#%s" % circle_id, "SK": "META"}).get("Item") or {}
    return meta.get("name", "your circle")


def _drop_push_subscription(member):
    _table().update_item(Key={"PK": member["PK"], "SK": member["SK"]},
                         UpdateExpression="REMOVE pushSubscription")
    log.info("push subscription removed member=%s", redact(member.get("SK")))


def _push(member, title, body):
    from pywebpush import WebPushException, webpush
    try:
        webpush(subscription_info=member["pushSubscription"],
                data=json.dumps({"title": title, "body": body}),
                vapid_private_key=_vapid_private_key(),
                vapid_claims={"sub": "mailto:%s" % os.environ.get("SES_FROM_EMAIL",
                                                                   "admin@aftercare.invalid")})
    except WebPushException as exc:
        if exc.status_code in (404, 410):
            # ponytail: dead subscription, drop it instead of retrying forever.
            _drop_push_subscription(member)
            return
        raise


def _email(member, subject, body):
    _client("ses").send_email(
        Source=os.environ["SES_FROM_EMAIL"],
        Destination={"ToAddresses": [member["email"]]},
        Message={"Subject": {"Data": subject}, "Body": {"Text": {"Data": body}}})


def _whatsapp(member, body):
    # Flag-gated by channels_for(); never called unless WHATSAPP_ENABLED == "true".
    phone_id = _client("ssm").get_parameter(
        Name="/aftercare/whatsapp/phone_id")["Parameter"]["Value"]
    _client("socialmessaging").send_whatsapp_message(
        originationPhoneNumberId=phone_id, metaApiVersion="v20.0",
        message=json.dumps({"messaging_product": "whatsapp", "to": member["whatsappNumber"],
                            "type": "text", "text": {"body": body}}).encode("utf-8"))


def _fan_out(circle_id, title, body, roles):
    for member in _members(circle_id):
        if member.get("role") not in roles:
            continue
        for channel in channels_for(member):
            try:
                if channel == "push":
                    _push(member, title, body)
                elif channel == "whatsapp":
                    _whatsapp(member, body)
                elif channel == "email":
                    _email(member, title, body)
                break  # first channel that works wins
            except Exception as exc:  # a channel/member failure never blocks the rest
                log.warning("notify failed channel=%s member=%s err=%s",
                            channel, redact(member.get("SK")), type(exc).__name__)


def send_reminder(circle_id, dose):
    """Copy names no medicine (lock screens and logs)."""
    slot = (dose.get("slot") or "").capitalize()
    body = "%s medicines for %s are due" % (slot, _circle_name(circle_id))
    _fan_out(circle_id, "AfterCare reminder", body, roles=("caregiver", "owner"))


def send_escalation(circle_id, dose):
    _fan_out(circle_id, "AfterCare alert", "A dose was missed. Please check.", roles=("owner",))


def _validate_subscription(subscription):
    if not isinstance(subscription, dict):
        raise ValueError("subscription is required")
    endpoint = subscription.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint.startswith("https://"):
        raise ValueError("subscription.endpoint must be an https URL")
    keys = subscription.get("keys")
    if not isinstance(keys, dict) or not keys.get("p256dh") or not keys.get("auth"):
        raise ValueError("subscription.keys.p256dh and keys.auth are required")


@route("POST", "/circles/{circleId}/push")
def register_push(event, params):
    circle_id = params["circleId"]
    principal = require(principal_from_event(event), circle_id)
    body = json.loads(event.get("body") or "{}")
    if not isinstance(body, dict):
        raise ValueError("body must be a JSON object")
    subscription = body.get("subscription")
    _validate_subscription(subscription)
    _table().update_item(
        Key={"PK": "CIRCLE#%s" % circle_id, "SK": "MEMBER#%s" % principal["sub"]},
        UpdateExpression="SET pushSubscription = :s",
        ExpressionAttributeValues={":s": subscription})
    return respond(204, {})
