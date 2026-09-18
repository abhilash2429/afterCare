import io
import json
import time
from decimal import Decimal

import boto3
import jwt
import pytest
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives.asymmetric import rsa
from moto import mock_aws

import api.auth as auth
import api.speech as speech
from api.auth import issue_circle_token
from api.handler import lambda_handler
from api.models import Medicine, Molecule, Plan
from api.speech import spoken_schedule, translate_plan


def _med(line_id, slots, brand, food="after"):
    return Medicine(lineId=line_id, rawText="", brand=brand,
                    molecules=[Molecule("aspirin", 75)], frequency="OD", slots=slots,
                    foodRelation=food, confidence=0.95, sourceBlockIds=["b1"],
                    needsConfirmation=False)


# spoken_schedule

def test_spoken_schedule_groups_by_slot():
    plan = Plan(planId="pl_1", circleId="ci_1",
                medicines=[_med("m1", ["morning"], "Ecosprin"),
                           _med("m2", ["morning"], "Pan"),
                           _med("m3", ["night"], "Atorva")])
    text = spoken_schedule(plan)
    assert "In the morning: Ecosprin, Pan" in text
    assert "In the night: Atorva" in text


def test_prn_medicine_is_not_spoken_in_any_slot():
    plan = Plan(planId="pl_1", circleId="ci_1", medicines=[_med("m1", [], "Sorbitrate")])
    assert spoken_schedule(plan) == ""


# translate_plan


class FakeTranslate:
    def __init__(self):
        self.calls = []

    def translate_text(self, Text, SourceLanguageCode, TargetLanguageCode):
        self.calls.append(Text)
        return {"TranslatedText": "[%s]%s" % (TargetLanguageCode, Text)}


def test_translate_plan_en_is_passthrough_and_makes_no_calls(monkeypatch):
    fake = FakeTranslate()
    monkeypatch.setattr(speech, "_translate", fake)
    plan = Plan(planId="pl_1", circleId="ci_1", medicines=[_med("m1", ["morning"], "Ecosprin")])
    out = translate_plan(plan, "en")
    assert out["medicines"]["m1"] == "morning: Ecosprin (after food)"
    assert out["slots"]["morning"] == "morning"
    assert fake.calls == []


def test_translate_plan_reuses_cached_phrases_across_medicines(monkeypatch):
    fake = FakeTranslate()
    monkeypatch.setattr(speech, "_translate", fake)
    plan = Plan(planId="pl_1", circleId="ci_1",
                medicines=[_med("m1", ["morning"], "Ecosprin"),
                           _med("m2", ["morning"], "Pan"),
                           _med("m3", ["night"], "Atorva")])
    out = translate_plan(plan, "kn")
    # "morning" and "after food" repeat across medicines but are only translated once each.
    assert sorted(fake.calls) == sorted({"morning", "after food", "night"})
    assert out["medicines"]["m1"].startswith("[kn]morning:")
    assert "Ecosprin" in out["medicines"]["m1"]  # brand name is never sent to Translate
    assert out["slots"] == {"morning": "[kn]morning", "night": "[kn]night"}


def test_translate_plan_does_not_translate_medicine_names(monkeypatch):
    fake = FakeTranslate()
    monkeypatch.setattr(speech, "_translate", fake)
    plan = Plan(planId="pl_1", circleId="ci_1", medicines=[_med("m1", ["morning"], "Ecosprin")])
    translate_plan(plan, "hi")
    assert "Ecosprin" not in fake.calls


# route: GET /plans/{planId}/audio

SECRET = "test-secret-that-is-at-least-32-bytes-long"


class FakeS3:
    def __init__(self, existing=None):
        self.existing = set(existing or ())
        self.puts = []

    def head_object(self, Bucket, Key):
        if Key not in self.existing:
            raise ClientError({"Error": {"Code": "404", "Message": "not found"}}, "HeadObject")

    def put_object(self, Bucket, Key, Body, ContentType):
        self.puts.append((Key, ContentType))
        self.existing.add(Key)

    def generate_presigned_url(self, op, Params, ExpiresIn):
        return "https://s3.example/%s?exp=%d" % (Params["Key"], ExpiresIn)


class FakePolly:
    def __init__(self):
        self.calls = []

    def synthesize_speech(self, **kw):
        self.calls.append(kw)
        return {"AudioStream": io.BytesIO(b"mp3-bytes")}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setattr(auth, "_secret", lambda: SECRET)
    monkeypatch.setenv("DOCS_BUCKET", "aftercare-docs-test")
    monkeypatch.setattr(speech, "BUCKET", "aftercare-docs-test")


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
        monkeypatch.setattr(speech, "_ddb", boto3.resource("dynamodb", region_name="ap-south-1"))
        yield t


@pytest.fixture
def s3(monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(speech, "_s3", fake)
    return fake


@pytest.fixture
def polly(monkeypatch):
    fake = FakePolly()
    monkeypatch.setattr(speech, "_polly", fake)
    return fake


@pytest.fixture
def translate(monkeypatch):
    fake = FakeTranslate()
    monkeypatch.setattr(speech, "_translate", fake)
    return fake


def _event(method, path, token=None, query=None):
    e = {"requestContext": {"http": {"method": method, "path": path}}, "headers": {},
         "queryStringParameters": query}
    if token:
        e["headers"]["authorization"] = "Bearer %s" % token
    return e


def _store_plan(table, plan):
    item = json.loads(json.dumps(plan.to_dict()), parse_float=Decimal)
    item["PK"] = "CIRCLE#%s" % plan.circleId
    item["SK"] = "PLAN#%s" % plan.planId
    table.put_item(Item=item)


def _plan():
    return Plan(planId="pl_1", circleId="ci_1",
                medicines=[_med("m1", ["morning"], "Ecosprin")])


def _make_owner(table, circle_id="ci_1", sub="u-owner"):
    table.put_item(Item={"PK": "CIRCLE#%s" % circle_id, "SK": "MEMBER#%s" % sub, "role": "owner"})


def test_audio_needs_a_token(table, s3, polly):
    res = lambda_handler(_event("GET", "/plans/pl_1/audio", query={"circleId": "ci_1"}), None)
    assert res["statusCode"] == 401


def test_audio_caregiver_wrong_circle_is_403(table, s3, polly):
    token = issue_circle_token("ci_A", "caregiver")
    res = lambda_handler(_event("GET", "/plans/pl_1/audio", token,
                                query={"circleId": "ci_B"}), None)
    assert res["statusCode"] == 403


def test_audio_plan_not_found_is_404(table, s3, polly):
    token = issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event("GET", "/plans/pl_1/audio", token), None)
    assert res["statusCode"] == 404


def test_audio_caregiver_token_supplies_circle_id_when_query_omits_it(table, s3, polly, translate):
    _store_plan(table, _plan())
    token = issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event("GET", "/plans/pl_1/audio", token), None)  # no circleId in query
    assert res["statusCode"] == 200


def test_audio_hindi_happy_path_caches_and_calls_polly(table, s3, polly, translate):
    _store_plan(table, _plan())
    token = issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event("GET", "/plans/pl_1/audio", token, query={"lang": "hi"}), None)
    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["spokenLanguage"] == "hi"
    assert body["url"].startswith("https://s3.example/audio/pl_1-")
    assert len(polly.calls) == 1
    call = polly.calls[0]
    assert call["VoiceId"] == "Kajal" and call["Engine"] == "neural"
    assert call["LanguageCode"] == "hi-IN"
    assert len(s3.puts) == 1

    # second call with the same content hits the S3 cache: no second synth.
    res2 = lambda_handler(_event("GET", "/plans/pl_1/audio", token, query={"lang": "hi"}), None)
    assert res2["statusCode"] == 200
    assert len(polly.calls) == 1


def test_audio_kannada_is_spoken_as_hindi(table, s3, polly, translate):
    _store_plan(table, _plan())
    token = issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event("GET", "/plans/pl_1/audio", token, query={"lang": "kn"}), None)
    body = json.loads(res["body"])
    assert body["spokenLanguage"] == "hi"
    assert polly.calls[0]["LanguageCode"] == "hi-IN"


def test_audio_english_skips_translate(table, s3, polly, translate):
    _store_plan(table, _plan())
    token = issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event("GET", "/plans/pl_1/audio", token, query={"lang": "en"}), None)
    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["spokenLanguage"] == "en"
    assert translate.calls == []
    assert polly.calls[0]["LanguageCode"] == "en-IN"


def test_audio_bad_lang_is_422(table, s3, polly):
    token = issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event("GET", "/plans/pl_1/audio", token, query={"lang": "fr"}), None)
    assert res["statusCode"] == 422


POOL = "ap-south-1_TEST"


def _owner_token(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update({"kid": "k1", "alg": "RS256", "use": "sig"})
    monkeypatch.setenv("USER_POOL_ID", POOL)
    monkeypatch.setenv("USER_POOL_CLIENT_ID", "client123")
    monkeypatch.setattr(auth, "_jwks_cache", {"keys": [jwk]})
    claims = {"sub": "u-owner", "aud": "client123", "token_use": "id",
              "iss": "https://cognito-idp.ap-south-1.amazonaws.com/%s" % POOL,
              "exp": int(time.time()) + 300, "iat": int(time.time())}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "k1"})


def test_audio_owner_needs_circle_id_query(table, s3, polly, translate, monkeypatch):
    token = _owner_token(monkeypatch)

    res = lambda_handler(_event("GET", "/plans/pl_1/audio", token), None)
    assert res["statusCode"] == 422  # owner token carries no circleId and none was given

    _store_plan(table, _plan())
    _make_owner(table)
    res2 = lambda_handler(_event("GET", "/plans/pl_1/audio", token,
                                 query={"circleId": "ci_1"}), None)
    assert res2["statusCode"] == 200
