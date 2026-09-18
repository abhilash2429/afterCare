from datetime import datetime

import boto3
from moto import mock_aws

from api.common import IST
from api.models import Plan
from scripts.seed_demo import seed


@mock_aws
def test_seed_is_idempotent_and_has_history():
    t = boto3.resource("dynamodb", region_name="ap-south-1").create_table(
        TableName="aftercare", BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"},
                   {"AttributeName": "SK", "KeyType": "RANGE"}],
        AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"},
                              {"AttributeName": "SK", "AttributeType": "S"}])
    now = datetime(2026, 9, 20, 10, 0, tzinfo=IST)
    seed(t, owner_sub="sub_owner", now=now)
    seed(t, owner_sub="sub_owner", now=now)
    items = t.query(KeyConditionExpression="PK = :p",
                    ExpressionAttributeValues={":p": "CIRCLE#ci_demo"})["Items"]
    doses = [i for i in items if i["SK"].startswith("DOSE#")]
    statuses = {d["status"] for d in doses}
    assert statuses == {"given", "missed", "pending"}
    assert [d["SK"] for d in doses if d["status"] == "missed"] == ["DOSE#2026-09-19#night"]
    assert all(d["status"] == "pending" for d in doses if d["date"] >= "2026-09-20")
    assert len(doses) == len({d["SK"] for d in doses})
    plan = Plan.from_dict(next(i for i in items if i["SK"] == "PLAN#pl_demo"))
    assert plan.status == "active" and len(plan.medicines) == 5
    assert any(i["SK"] == "MEMBER#sub_owner" and i["role"] == "owner" for i in items)
