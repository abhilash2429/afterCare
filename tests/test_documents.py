import io
import json
import time

import boto3
import jwt
import pytest
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives.asymmetric import rsa
from moto import mock_aws

import api.auth as auth
import api.documents as documents
import api.plans as plans_mod
from api.auth import issue_circle_token
from api.extract import ExtractionFailed
from api.handler import ROUTES, lambda_handler
from api.models import Medicine, Molecule, Plan, RedFlags

SECRET = "test-secret-that-is-at-least-32-bytes-long"


class FakeS3:
    def __init__(self):
        self.calls = []

    def generate_presigned_url(self, op, Params=None, ExpiresIn=None):
        self.calls.append({"op": op, "Params": dict(Params or {}), "ExpiresIn": ExpiresIn})
        return "https://s3.example/%s?exp=%s" % (Params["Key"], ExpiresIn)


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setattr(auth, "_secret", lambda: SECRET)
    monkeypatch.setenv("DOCS_BUCKET", "test-bucket")
    monkeypatch.setattr(documents, "BUCKET", "test-bucket")


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
        monkeypatch.setattr(documents, "_ddb", boto3.resource("dynamodb", region_name="ap-south-1"))
        monkeypatch.setattr(plans_mod, "_ddb", documents._ddb)
        s3 = boto3.client("s3", region_name="ap-south-1")
        try:
            s3.create_bucket(Bucket="test-bucket",
                             CreateBucketConfiguration={"LocationConstraint": "ap-south-1"})
        except Exception:
            pass
        fake = FakeS3()
        monkeypatch.setattr(documents, "_s3", fake)
        yield t


@pytest.fixture
def s3calls(table):
    return documents._s3


def _event(method, path, body=None, token=None, raw_body=None):
    e = {"requestContext": {"http": {"method": method, "path": path}},
         "headers": {}, "queryStringParameters": None}
    if token:
        e["headers"]["authorization"] = "Bearer %s" % token
    if raw_body is not None:
        e["body"] = raw_body
    elif body is not None:
        e["body"] = json.dumps(body)
    return e


def _post(path, body, token=None):
    return lambda_handler(_event("POST", path, body, token=token), None)


POOL = "ap-south-1_TEST"


def _owner_token(monkeypatch, sub="u-owner"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update({"kid": "k1", "alg": "RS256", "use": "sig"})
    monkeypatch.setenv("USER_POOL_ID", POOL)
    monkeypatch.setenv("USER_POOL_CLIENT_ID", "client123")
    monkeypatch.setattr(auth, "_jwks_cache", {"keys": [jwk]})
    claims = {"sub": sub, "aud": "client123", "token_use": "id",
              "iss": "https://cognito-idp.ap-south-1.amazonaws.com/%s" % POOL,
              "exp": int(time.time()) + 300, "iat": int(time.time())}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "k1"})


def _make_owner(table, circle_id="ci_1", sub="u-owner"):
    table.put_item(Item={"PK": "CIRCLE#%s" % circle_id, "SK": "MEMBER#%s" % sub, "role": "owner"})


def _plan(circle_id="ci_1", plan_id="pl_1"):
    return Plan(planId=plan_id, circleId=circle_id,
                medicines=[Medicine(lineId="m1", rawText="T. Dolo",
                                    molecules=[Molecule("paracetamol", 650)],
                                    frequency="OD", slots=["morning"],
                                    confidence=0.95, sourceBlockIds=["b1"],
                                    needsConfirmation=False)],
                redFlags=RedFlags(source="generic", text="generic", sourceBlockIds=[]),
                status="draft")


# --- A1 auth ---

def test_create_needs_token(table):
    res = _post("/documents", {"circleId": "ci_1", "pageCount": 1, "contentType": "image/jpeg"})
    assert res["statusCode"] == 401


def test_create_caregiver_allowed(table):
    token = issue_circle_token("ci_1", "caregiver")
    res = _post("/documents", {"circleId": "ci_1", "pageCount": 1,
                               "contentType": "image/jpeg"}, token=token)
    assert res["statusCode"] == 201


def test_create_owner_allowed(table, monkeypatch):
    token = _owner_token(monkeypatch)
    _make_owner(table)
    res = _post("/documents", {"circleId": "ci_1", "pageCount": 1,
                               "contentType": "image/jpeg"}, token=token)
    assert res["statusCode"] == 201


def test_create_caregiver_wrong_circle_is_403(table):
    token = issue_circle_token("ci_A", "caregiver")
    res = _post("/documents", {"circleId": "ci_B", "pageCount": 1,
                               "contentType": "image/jpeg"}, token=token)
    assert res["statusCode"] == 403


def test_create_caregiver_token_supplies_circle_when_body_omits_it(table):
    token = issue_circle_token("ci_1", "caregiver")
    res = _post("/documents", {"pageCount": 1, "contentType": "image/jpeg"}, token=token)
    assert res["statusCode"] == 201
    body = json.loads(res["body"])
    assert body["uploads"][0]["key"].startswith("circles/ci_1/")


def test_create_missing_circle_is_422(table, monkeypatch):
    token = _owner_token(monkeypatch)
    _make_owner(table, circle_id="ci_1")
    res = _post("/documents", {"pageCount": 1, "contentType": "image/jpeg"}, token=token)
    assert res["statusCode"] == 422


def test_extract_needs_token(table):
    res = _post("/documents/doc_1/extract", {"circleId": "ci_1"})
    assert res["statusCode"] == 401


def test_extract_caregiver_is_403(table, monkeypatch):
    token = issue_circle_token("ci_1", "caregiver")
    monkeypatch.setattr(documents, "extract_plan", lambda keys, cid: _plan())
    # seed a doc so we get past 404 to the auth check (auth runs first anyway)
    table.put_item(Item={"PK": "CIRCLE#ci_1", "SK": "DOC#doc_1", "documentId": "doc_1",
                         "keys": ["circles/ci_1/doc_1/p1.jpg"]})
    res = _post("/documents/doc_1/extract", {"circleId": "ci_1"}, token=token)
    assert res["statusCode"] == 403


def test_extract_owner_missing_circle_is_422(table, monkeypatch):
    token = _owner_token(monkeypatch)
    _make_owner(table)
    res = _post("/documents/doc_1/extract", {}, token=token)
    assert res["statusCode"] == 422


# --- A2 content types ---

def test_rejects_pdf_content_type(table):
    token = issue_circle_token("ci_1", "caregiver")
    res = _post("/documents", {"circleId": "ci_1", "pageCount": 1,
                               "contentType": "application/pdf"}, token=token)
    assert res["statusCode"] == 422


def test_rejects_tiff_content_type(table):
    token = issue_circle_token("ci_1", "caregiver")
    res = _post("/documents", {"circleId": "ci_1", "pageCount": 1,
                               "contentType": "image/tiff"}, token=token)
    assert res["statusCode"] == 422


def test_accepts_png(table):
    token = issue_circle_token("ci_1", "caregiver")
    res = _post("/documents", {"circleId": "ci_1", "pageCount": 1,
                               "contentType": "image/png"}, token=token)
    assert res["statusCode"] == 201
    body = json.loads(res["body"])
    assert body["uploads"][0]["key"].endswith(".png")


def test_rejects_too_many_pages(table):
    token = issue_circle_token("ci_1", "caregiver")
    res = _post("/documents", {"circleId": "ci_1", "pageCount": 40,
                               "contentType": "image/jpeg"}, token=token)
    assert res["statusCode"] == 422


# --- A3 S3 keys + presigned ---

def test_create_returns_uploads_shape_and_key_format(table):
    token = issue_circle_token("ci_1", "caregiver")
    res = _post("/documents", {"circleId": "ci_1", "pageCount": 2,
                               "contentType": "image/jpeg"}, token=token)
    assert res["statusCode"] == 201
    body = json.loads(res["body"])
    assert set(body) == {"documentId", "uploads"}
    assert len(body["uploads"]) == 2
    for i, u in enumerate(body["uploads"], start=1):
        assert set(u) == {"page", "key", "uploadUrl"}
        assert u["page"] == i
        assert u["key"] == "circles/ci_1/%s/p%d.jpg" % (body["documentId"], i)


def test_presigned_put_uses_contenttype_and_900s(table, s3calls):
    token = issue_circle_token("ci_1", "caregiver")
    _post("/documents", {"circleId": "ci_1", "pageCount": 1,
                         "contentType": "image/jpeg"}, token=token)
    assert len(s3calls.calls) == 1
    call = s3calls.calls[0]
    assert call["op"] == "put_object"
    assert call["Params"]["Bucket"] == "test-bucket"
    assert call["Params"]["ContentType"] == "image/jpeg"
    assert call["Params"]["Key"].startswith("circles/ci_1/doc_")
    assert call["ExpiresIn"] == 900


# --- A4 storage ---

def test_doc_item_stored_with_ttl_fields_and_no_text(table):
    token = issue_circle_token("ci_1", "caregiver", )
    # issue_circle_token(sub) default random; capture uploadedBy via decode
    res = _post("/documents", {"circleId": "ci_1", "pageCount": 2,
                               "contentType": "image/jpeg"}, token=token)
    body = json.loads(res["body"])
    doc_id = body["documentId"]
    item = table.get_item(Key={"PK": "CIRCLE#ci_1", "SK": "DOC#%s" % doc_id})["Item"]
    assert item["documentId"] == doc_id
    assert item["keys"] == [u["key"] for u in body["uploads"]]
    assert item["pageCount"] == 2
    assert item["contentType"] == "image/jpeg"
    assert isinstance(item["uploadedBy"], str) and item["uploadedBy"]
    assert isinstance(item["createdAt"], str) and item["createdAt"]
    assert abs(item["expiresAt"] - (int(time.time()) + 30 * 24 * 3600)) < 120
    # never store document text
    blob = json.dumps(item, default=str).lower()
    assert "paracetamol" not in blob
    for forbidden in ("documentText", "text", "medicines", "rawText"):
        assert forbidden not in item


# --- A5 extract ---

def _seed_doc(table, doc_id="doc_1", circle_id="ci_1", keys=None, plan_id=None):
    item = {"PK": "CIRCLE#%s" % circle_id, "SK": "DOC#%s" % doc_id,
            "documentId": doc_id, "circleId": circle_id,
            "keys": keys or ["circles/%s/%s/p1.jpg" % (circle_id, doc_id)],
            "pageCount": 1, "contentType": "image/jpeg",
            "uploadedBy": "u-owner", "createdAt": "2026-09-18T00:00:00+05:30",
            "expiresAt": int(time.time()) + 30 * 24 * 3600}
    if plan_id:
        item["planId"] = plan_id
    table.put_item(Item=item)
    return item


def test_extract_missing_doc_is_404(table, monkeypatch):
    token = _owner_token(monkeypatch)
    _make_owner(table)
    monkeypatch.setattr(documents, "extract_plan", lambda keys, cid: _plan())
    res = _post("/documents/nope/extract", {"circleId": "ci_1"}, token=token)
    assert res["statusCode"] == 404


def test_extract_happy_path_saves_plan_and_records_planId(table, monkeypatch):
    token = _owner_token(monkeypatch)
    _make_owner(table)
    _seed_doc(table)
    made = _plan()
    seen = {}

    def fake_extract(keys, circle_id):
        seen["keys"] = keys
        seen["circle_id"] = circle_id
        return made

    monkeypatch.setattr(documents, "extract_plan", fake_extract)
    res = _post("/documents/doc_1/extract", {"circleId": "ci_1"}, token=token)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["planId"] == made.planId
    assert body["status"] == "draft"
    assert seen["keys"] == ["circles/ci_1/doc_1/p1.jpg"]
    assert seen["circle_id"] == "ci_1"
    plan_item = table.get_item(Key={"PK": "CIRCLE#ci_1", "SK": "PLAN#%s" % made.planId})["Item"]
    assert plan_item["sourceDocumentIds"] == ["doc_1"]
    doc = table.get_item(Key={"PK": "CIRCLE#ci_1", "SK": "DOC#doc_1"})["Item"]
    assert doc["planId"] == made.planId


def test_extract_idempotent_returns_same_plan_without_rerun(table, monkeypatch):
    token = _owner_token(monkeypatch)
    _make_owner(table)
    made = _plan()
    plan_item = json.loads(json.dumps(made.to_dict()), parse_float=str)
    plan_item.update({"PK": "CIRCLE#ci_1", "SK": "PLAN#%s" % made.planId})
    table.put_item(Item=plan_item)
    _seed_doc(table, plan_id=made.planId)

    def boom(keys, circle_id):
        raise AssertionError("model must not run when planId already recorded")

    monkeypatch.setattr(documents, "extract_plan", boom)
    res = _post("/documents/doc_1/extract", {"circleId": "ci_1"}, token=token)
    assert res["statusCode"] == 200
    assert json.loads(res["body"])["planId"] == made.planId


# --- A6 errors ---

def test_extraction_failed_maps_to_422(table, monkeypatch):
    token = _owner_token(monkeypatch)
    _make_owner(table)
    _seed_doc(table)

    def fail(keys, circle_id):
        raise ExtractionFailed("model returned no JSON")

    monkeypatch.setattr(documents, "extract_plan", fail)
    res = _post("/documents/doc_1/extract", {"circleId": "ci_1"}, token=token)
    assert res["statusCode"] == 422
    assert json.loads(res["body"])["code"] == "extraction_failed"


def test_client_error_during_extract_maps_to_422(table, monkeypatch):
    token = _owner_token(monkeypatch)
    _make_owner(table)
    _seed_doc(table)

    def fail(keys, circle_id):
        raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "missing"}}, "GetObject")

    monkeypatch.setattr(documents, "extract_plan", fail)
    res = _post("/documents/doc_1/extract", {"circleId": "ci_1"}, token=token)
    assert res["statusCode"] == 422
    assert json.loads(res["body"])["code"] == "extraction_failed"


def test_handler_maps_extraction_failed_before_valueerror(monkeypatch):
    from api.handler import lambda_handler as lh

    def boom(event, params):
        raise ExtractionFailed("bad model output")

    monkeypatch.setitem(ROUTES, ("GET", "/__t/extract-fail"), boom)
    res = lh({"requestContext": {"http": {"method": "GET", "path": "/__t/extract-fail"}}}, None)
    assert res["statusCode"] == 422
    assert json.loads(res["body"])["code"] == "extraction_failed"
