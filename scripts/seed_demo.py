"""Seed the demo circle used in the video. Idempotent: it overwrites ci_demo.

Usage: python -m scripts.seed_demo [--owner-sub <cognito sub>] [--web-origin https://...]

--owner-sub makes that Cognito user the circle owner. The script also prints a
fresh one-time caregiver invite link (valid 7 days) for the phone in the video.
"""
import argparse
import hashlib
import json
import secrets
import time
from datetime import timedelta

import boto3

from api.common import REGION, TABLE, now_ist
from api.doses import build_doses
from api.models import DEFAULT_SLOT_TIMES, Medicine, Molecule, Plan, RedFlags

CIRCLE = "ci_demo"
PLAN = "pl_demo"

MEDS = [
    ("m1", "Ecosprin", "aspirin", 75, "OD", ["morning"], "after", 30),
    ("m2", "Clopitab", "clopidogrel", 75, "OD", ["night"], "after", 30),
    ("m3", "Atorva", "atorvastatin", 40, "HS", ["bedtime"], "unspecified", 30),
    ("m4", "Pan", "pantoprazole", 40, "BD", ["morning", "night"], "before", 14),
    ("m5", "Glycomet GP1", "metformin", 500, "BD", ["morning", "night"], "after", 30),
]


def demo_plan():
    medicines = [Medicine(lineId=i, rawText="T. %s %s %s" % (brand, strength, freq), brand=brand,
                          molecules=[Molecule(mol, strength)], frequency=freq,
                          slots=slots, foodRelation=food, durationDays=days,
                          confidence=0.96, sourceBlockIds=["b1"], needsConfirmation=False)
                 for i, brand, mol, strength, freq, slots, food, days in MEDS]
    return Plan(planId=PLAN, circleId=CIRCLE, medicines=medicines,
                redFlags=RedFlags(source="document",
                                  text="Report immediately if chest pain returns, "
                                       "breathlessness at rest, bleeding or black stools.",
                                  sourceBlockIds=["b81"]),
                patientName="Ramesh K.", language="kn", status="active")


def dose_status(dose, now):
    """Past days given except yesterday's night dose (missed); today pending."""
    today = now.date().isoformat()
    yesterday = (now.date() - timedelta(days=1)).isoformat()
    if dose.date >= today:
        return "pending"
    if dose.date == yesterday and dose.slot == "night":
        return "missed"
    return "given"


def seed(table, owner_sub=None, now=None):
    now = now or now_ist()
    pk = "CIRCLE#%s" % CIRCLE
    old = table.query(KeyConditionExpression="PK = :p", ExpressionAttributeValues={":p": pk})
    with table.batch_writer() as batch:
        for item in old.get("Items", []):
            batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

    plan = demo_plan()
    table.put_item(Item={"PK": pk, "SK": "META", "circleId": CIRCLE,
                         "name": "Kulkarni family", "language": "kn",
                         "slotTimes": dict(DEFAULT_SLOT_TIMES), "escalationMinutes": 60})
    if owner_sub:
        table.put_item(Item={"PK": pk, "SK": "MEMBER#%s" % owner_sub, "role": "owner"})
    item = plan.to_dict()
    item.update({"PK": pk, "SK": "PLAN#%s" % PLAN})
    table.put_item(Item=json.loads(json.dumps(item), parse_float=str))

    doses = build_doses(plan, now.date() - timedelta(days=3), days=5)
    with table.batch_writer() as batch:
        for dose in doses:
            status = dose_status(dose, now)
            batch.put_item(Item={"PK": pk, "SK": "DOSE#%s#%s" % (dose.date, dose.slot),
                                 "doseId": dose.doseId, "date": dose.date,
                                 "slot": dose.slot, "status": status,
                                 "givenAt": now.isoformat() if status == "given" else None,
                                 "givenBy": "cg_demo" if status == "given" else None,
                                 "medicineLineIds": dose.medicineLineIds})

    token = secrets.token_urlsafe(24)
    table.put_item(Item={"PK": "INVITE#%s" % hashlib.sha256(token.encode()).hexdigest(),
                         "SK": "META", "circleId": CIRCLE, "role": "caregiver",
                         "expiresAt": int(time.time()) + 7 * 24 * 3600, "used": False})
    return len(doses), token


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner-sub")
    ap.add_argument("--web-origin", default="http://localhost:3000")
    args = ap.parse_args()
    table = boto3.resource("dynamodb", region_name=REGION).Table(TABLE)
    count, token = seed(table, args.owner_sub)
    print("seeded %s: %d doses" % (CIRCLE, count))
    print("caregiver invite: %s/join?c=%s&t=%s" % (args.web_origin, CIRCLE, token))


if __name__ == "__main__":
    main()
