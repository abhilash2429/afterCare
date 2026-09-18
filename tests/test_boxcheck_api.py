import inspect
import io
import json
import time

import boto3
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from moto import mock_aws

import api.auth as auth
import api.plans as plans
from api import extract
from api.boxcheck import MESSAGES
from api.handler import lambda_handler
from api.models import Medicine, Molecule, Plan, RedFlags

SECRET = "test-secret-that-is-at-least-32-bytes-long"


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setattr(auth, "_secret", lambda: SECRET)
    monkeypatch.setenv("DOCS_BUCKET", "aftercare-docs-test")


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
        monkeypatch.setattr(plans, "_ddb", boto3.resource("dynamodb", region_name="ap-south-1"))
        import api.boxcheck_api as mod
        monkeypatch.setattr(mod, "_ddb", boto3.resource("dynamodb", region_name="ap-south-1"))
        monkeypatch.setattr(mod, "TABLE", "aftercare")
        monkeypatch.setattr(mod, "BUCKET", "aftercare-docs-test")
        yield t


class FakeS3:
    def __init__(self, blobs=None):
        self.blobs = dict(blobs or {})
        self.keys_seen = []

    def get_object(self, Bucket, Key):
        self.keys_seen.append(Key)
        return {"Body": io.BytesIO(self.blobs.get(Key, b"img-bytes"))}


@pytest.fixture
def s3fake(monkeypatch):
    import api.boxcheck_api as mod
    fake = FakeS3()
    monkeypatch.setattr(mod, "_s3", fake)
    return fake


def _med(line_id="m1", name="aspirin", strength=75, **kw):
    base = dict(lineId=line_id, rawText="", molecules=[Molecule(name, strength)],
                frequency="OD", slots=["morning"],
                confidence=0.95, sourceBlockIds=["b1"], needsConfirmation=False)
    base.update(kw)
    return Medicine(**base)


def _plan(**kw):
    base = dict(planId="pl_1", circleId="ci_1", medicines=[_med()],
                redFlags=RedFlags(source="document", text="chest pain", sourceBlockIds=["b9"]))
    base.update(kw)
    return Plan(**base)


def _store_plan(table, plan):
    item = json.loads(json.dumps(plan.to_dict()), parse_float=float)
    item["PK"] = "CIRCLE#%s" % plan.circleId
    item["SK"] = "PLAN#%s" % plan.planId
    table.put_item(Item=json.loads(json.dumps(item), parse_float=str))


def _store_doc(table, circle_id="ci_1", doc_id="doc_1", keys=None):
    table.put_item(Item={"PK": "CIRCLE#%s" % circle_id, "SK": "DOC#%s" % doc_id,
                         "documentId": doc_id, "keys": list(keys or [])})


def _event(body=None, token=None, raw_body=None):
    e = {"requestContext": {"http": {"method": "POST", "path": "/boxcheck"}},
         "headers": {}}
    if token:
        e["headers"]["authorization"] = "Bearer %s" % token
    if raw_body is not None:
        e["body"] = raw_body
    elif body is not None:
        e["body"] = json.dumps(body)
    return e


def _words(*texts):
    return [{"id": "w%d" % i, "text": t,
             "box": {"Left": 0.1, "Top": 0.1, "Width": 0.1, "Height": 0.02}}
            for i, t in enumerate(texts)]


def _mock_vision(monkeypatch, words_by_key, strips_by_key=None, model_strips=None,
                 lookup=None):
    import api.boxcheck_api as mod
    strips_by_key = strips_by_key or {}

    def fake_textract(key):
        return list(words_by_key.get(key, []))

    def fake_model(image_bytes, image_format, words, model_id, prompt=None):
        fake_model.seen.append({"image": image_bytes, "format": image_format,
                                "prompt": prompt})
        key = fake_model.key_for.pop(0) if fake_model.key_for else None
        if key is not None and key in strips_by_key:
            return {"strips": strips_by_key[key]}
        return {"strips": list(model_strips or [])}

    fake_model.seen = []
    # keys are consumed in doc order; tests set this via doc keys
    fake_model.key_for = list(words_by_key.keys())
    # _read_strips only gets image bytes, so route image reads in doc order;
    # map sequentially to keys for per-photo raw payloads.
    monkeypatch.setattr(mod, "textract_words", fake_textract)
    monkeypatch.setattr(mod, "_call_model", fake_model)
    if lookup is not None:
        monkeypatch.setattr(mod, "lookup_brand", lookup)
    return fake_model


# --- A1: _call_model takes an optional prompt defaulting to PROMPT ---

def test_call_model_prompt_defaults_to_extraction_prompt():
    sig = inspect.signature(extract._call_model)
    assert "prompt" in sig.parameters
    assert sig.parameters["prompt"].default == extract.PROMPT


def test_read_strips_sends_strip_prompt(monkeypatch):
    import api.boxcheck_api as mod
    seen = {}

    def fake(image_bytes, image_format, words, model_id, prompt=None):
        seen.update(prompt=prompt, fmt=image_format)
        return {"strips": []}

    monkeypatch.setattr(mod, "_call_model", fake)
    mod._read_strips(b"x", "png")
    assert seen["prompt"] == mod.STRIP_PROMPT
    assert seen["fmt"] == "png"


def test_old_callers_still_work_with_four_args(monkeypatch):
    # extract_plan calls _call_model with 4 positional args; default prompt keeps it working.
    captured = {}

    def fake(image, fmt, words, model_id, prompt=extract.PROMPT):
        captured["prompt"] = prompt
        return {"medicines": [], "redFlags": {"present": False}}

    monkeypatch.setattr(extract, "_call_model", fake)
    monkeypatch.setattr(extract, "textract_words", lambda key: [{"id": "w1", "text": "x",
        "box": {"Left": 0, "Top": 0, "Width": 0.1, "Height": 0.1}}] * 25)

    class _S3:
        def get_object(self, Bucket, Key):
            return {"Body": io.BytesIO(b"img")}

    monkeypatch.setattr(extract, "_s3", _S3())
    plan = extract.extract_plan(["c/doc.png"], "c1", model_id="m")
    assert captured["prompt"] == extract.PROMPT
    assert plan.medicines == []


# --- A3: grounded composition wins over brand ---

def test_grounded_composition_wins_over_brand(table, s3fake, monkeypatch):
    _store_plan(table, _plan())
    _store_doc(table, keys=["k1.png"])
    words = _words("Aspirin", "75mg", "Unknown", "Brand", "X")
    fake = _mock_vision(monkeypatch, {"k1.png": words},
                        strips_by_key={"k1.png": [
                            {"brandText": "Unknown Brand X",
                             "compositionText": "Aspirin (75mg)"}]},
                        lookup=lambda b: [])
    token = auth.issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event({"circleId": "ci_1", "planId": "pl_1",
                                 "documentId": "doc_1"}, token=token), None)
    assert res["statusCode"] == 200
    items = json.loads(res["body"])["items"]
    assert items[0]["verdict"] == "matched" and items[0]["reason"] == "exact_match"
    assert items[0]["stripMolecules"] == [{"name": "aspirin", "strengthMg": 75,
                                           "unit": "mg"}]
    assert items[0]["stripBrandText"] == "Unknown Brand X"
    assert fake.seen[0]["prompt"] is not None


def test_ungrounded_composition_falls_back_to_brand_lookup(table, s3fake, monkeypatch):
    _store_plan(table, _plan())
    _store_doc(table, keys=["k1.png"])
    # Photo shows Ecosprin only; model-guessed paracetamol composition is not on the photo.
    words = _words("Ecosprin", "75")
    _mock_vision(monkeypatch, {"k1.png": words},
                 strips_by_key={"k1.png": [
                     {"brandText": "Ecosprin",
                      "compositionText": "Paracetamol (500mg)"}]},
                 lookup=lambda b: [Molecule("aspirin", 75)] if b == "Ecosprin" else [])
    token = auth.issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event({"circleId": "ci_1", "planId": "pl_1",
                                 "documentId": "doc_1"}, token=token), None)
    assert res["statusCode"] == 200
    items = json.loads(res["body"])["items"]
    assert items[0]["verdict"] == "matched" and items[0]["reason"] == "exact_match"
    assert items[0]["stripMolecules"][0]["name"] == "aspirin"


def test_nothing_grounded_is_unreadable_strip(table, s3fake, monkeypatch):
    _store_plan(table, _plan())
    _store_doc(table, keys=["k1.png"])
    words = _words("blurry", "photo")
    _mock_vision(monkeypatch, {"k1.png": words},
                 strips_by_key={"k1.png": [
                     {"brandText": "Ecosprin", "compositionText": "Aspirin (75mg)"}]},
                 lookup=lambda b: [])
    token = auth.issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event({"circleId": "ci_1", "planId": "pl_1",
                                 "documentId": "doc_1"}, token=token), None)
    assert res["statusCode"] == 200
    by_reason = {i["reason"]: i for i in json.loads(res["body"])["items"]}
    assert by_reason["unreadable_strip"]["verdict"] == "check"
    assert by_reason["unreadable_strip"]["stripBrandText"] is None
    assert by_reason["unreadable_strip"]["stripMolecules"] == []
    assert by_reason["missing_from_box"]["verdict"] == "do_not_take"


def test_ungrounded_brand_becomes_none_but_grounded_composition_still_matches(
        table, s3fake, monkeypatch):
    _store_plan(table, _plan())
    _store_doc(table, keys=["k1.png"])
    words = _words("Aspirin", "75mg")
    _mock_vision(monkeypatch, {"k1.png": words},
                 strips_by_key={"k1.png": [
                     {"brandText": "MadeUpBrand", "compositionText": "Aspirin (75mg)"}]},
                 lookup=lambda b: [])
    token = auth.issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event({"circleId": "ci_1", "planId": "pl_1",
                                 "documentId": "doc_1"}, token=token), None)
    items = json.loads(res["body"])["items"]
    assert items[0]["reason"] == "brand_unreadable"
    assert items[0]["stripBrandText"] is None


# --- A2: auth ---

def test_caregiver_of_another_circle_is_403(table, s3fake, monkeypatch):
    _store_plan(table, _plan(circleId="ci_B", planId="pl_B"))
    _store_doc(table, circle_id="ci_B", doc_id="doc_B", keys=["k1.png"])
    _mock_vision(monkeypatch, {"k1.png": []}, model_strips=[])
    token = auth.issue_circle_token("ci_A", "caregiver")
    res = lambda_handler(_event({"circleId": "ci_B", "planId": "pl_B",
                                 "documentId": "doc_B"}, token=token), None)
    assert res["statusCode"] == 403


def test_require_runs_before_data_reads(table, s3fake, monkeypatch):
    # Wrong-circle token against ids that do not exist must still be 403, not 404.
    import api.boxcheck_api as mod
    called = {"db": False}
    orig_load = plans._load

    def spy_load(cid, pid):
        called["db"] = True
        return orig_load(cid, pid)

    monkeypatch.setattr(plans, "_load", spy_load)
    monkeypatch.setattr(mod, "textract_words", lambda k: (_ for _ in ()).throw(
        AssertionError("textract must not run before require")))
    token = auth.issue_circle_token("ci_A", "caregiver")
    res = lambda_handler(_event({"circleId": "ci_B", "planId": "nope",
                                 "documentId": "nope"}, token=token), None)
    assert res["statusCode"] == 403
    assert called["db"] is False


def test_missing_doc_is_404(table, s3fake, monkeypatch):
    _store_plan(table, _plan())
    _mock_vision(monkeypatch, {}, model_strips=[])
    token = auth.issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event({"circleId": "ci_1", "planId": "pl_1",
                                 "documentId": "nope"}, token=token), None)
    assert res["statusCode"] == 404
    assert json.loads(res["body"])["code"] == "not_found"


def test_missing_plan_is_404(table, s3fake, monkeypatch):
    _store_doc(table, keys=["k1.png"])
    _mock_vision(monkeypatch, {"k1.png": []}, model_strips=[])
    token = auth.issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event({"circleId": "ci_1", "planId": "nope",
                                 "documentId": "doc_1"}, token=token), None)
    assert res["statusCode"] == 404


def test_caregiver_token_supplies_circle_when_body_omits_it(table, s3fake, monkeypatch):
    _store_plan(table, _plan())
    _store_doc(table, keys=[])
    _mock_vision(monkeypatch, {}, model_strips=[])
    token = auth.issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event({"planId": "pl_1", "documentId": "doc_1"},
                                token=token), None)
    assert res["statusCode"] == 200


def test_owner_token_without_circle_is_422(table, s3fake, monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update({"kid": "k1", "alg": "RS256", "use": "sig"})
    pool = "ap-south-1_TEST"
    monkeypatch.setenv("USER_POOL_ID", pool)
    monkeypatch.setenv("USER_POOL_CLIENT_ID", "client123")
    monkeypatch.setattr(auth, "_jwks_cache", {"keys": [jwk]})
    claims = {"sub": "u-owner", "aud": "client123", "token_use": "id",
              "iss": "https://cognito-idp.ap-south-1.amazonaws.com/%s" % pool,
              "exp": int(time.time()) + 300, "iat": int(time.time())}
    token = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "k1"})
    res = lambda_handler(_event({"planId": "pl_1", "documentId": "doc_1"},
                                token=token), None)
    assert res["statusCode"] == 422


def test_owner_with_circle_and_membership_is_allowed(table, s3fake, monkeypatch):
    _store_plan(table, _plan())
    _store_doc(table, keys=[])
    _mock_vision(monkeypatch, {}, model_strips=[])
    table.put_item(Item={"PK": "CIRCLE#ci_1", "SK": "MEMBER#u-owner", "role": "owner"})
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    jwk.update({"kid": "k1", "alg": "RS256", "use": "sig"})
    pool = "ap-south-1_TEST"
    monkeypatch.setenv("USER_POOL_ID", pool)
    monkeypatch.setenv("USER_POOL_CLIENT_ID", "client123")
    monkeypatch.setattr(auth, "_jwks_cache", {"keys": [jwk]})
    claims = {"sub": "u-owner", "aud": "client123", "token_use": "id",
              "iss": "https://cognito-idp.ap-south-1.amazonaws.com/%s" % pool,
              "exp": int(time.time()) + 300, "iat": int(time.time())}
    token = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "k1"})
    res = lambda_handler(_event({"circleId": "ci_1", "planId": "pl_1",
                                 "documentId": "doc_1"}, token=token), None)
    assert res["statusCode"] == 200


def test_missing_ids_is_422(table, s3fake, monkeypatch):
    _mock_vision(monkeypatch, {}, model_strips=[])
    token = auth.issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event({"circleId": "ci_1", "planId": "pl_1"},
                                token=token), None)
    assert res["statusCode"] == 422


def test_needs_a_token(table, s3fake):
    res = lambda_handler(_event({"circleId": "ci_1", "planId": "pl_1",
                                 "documentId": "doc_1"}), None)
    assert res["statusCode"] == 401


# --- A4: image format from the key extension ---

def test_image_format_follows_key_extension(table, s3fake, monkeypatch):
    _store_plan(table, _plan())
    _store_doc(table, keys=["a.png", "b.JPG", "c.jpeg"])
    words = _words("Aspirin", "75mg")
    fake = _mock_vision(monkeypatch, {"a.png": words, "b.JPG": words, "c.jpeg": words},
                        model_strips=[])
    token = auth.issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event({"circleId": "ci_1", "planId": "pl_1",
                                 "documentId": "doc_1"}, token=token), None)
    assert res["statusCode"] == 200
    assert [s["format"] for s in fake.seen] == ["png", "jpeg", "jpeg"]


def test_unsupported_image_extension_is_422(table, s3fake, monkeypatch):
    _store_plan(table, _plan())
    _store_doc(table, keys=["a.gif"])
    _mock_vision(monkeypatch, {"a.gif": []}, model_strips=[])
    token = auth.issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event({"circleId": "ci_1", "planId": "pl_1",
                                 "documentId": "doc_1"}, token=token), None)
    assert res["statusCode"] == 422


# --- A5/A6: contract shape, copy source, full route ---

def test_full_route_returns_contract_shape(table, s3fake, monkeypatch):
    _store_plan(table, _plan())
    _store_doc(table, keys=["k1.png"])
    words = _words("Aspirin", "75mg", "Ecosprin")
    _mock_vision(monkeypatch, {"k1.png": words},
                 strips_by_key={"k1.png": [
                     {"brandText": "Ecosprin", "compositionText": "Aspirin (75mg)"}]},
                 lookup=lambda b: [])
    token = auth.issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event({"circleId": "ci_1", "planId": "pl_1",
                                 "documentId": "doc_1"}, token=token), None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert set(body) == {"items"}
    assert isinstance(body["items"], list) and body["items"]
    allowed_verdicts = {"matched", "check", "do_not_take"}
    allowed_reasons = {"exact_match", "strength_mismatch", "combination_extra",
                       "brand_unreadable", "missing_from_box", "not_prescribed",
                       "duplicate_molecule", "combination_strip", "unreadable_strip",
                       "strength_unreadable"}
    for item in body["items"]:
        assert set(item) == {"verdict", "reason", "message", "prescribedLineId",
                             "stripBrandText", "stripMolecules"}
        assert item["verdict"] in allowed_verdicts
        assert item["reason"] in allowed_reasons
        assert item["message"] in MESSAGES.values()
        assert item["message"] == MESSAGES[item["reason"]]
        assert "safe" not in item["message"].lower()
        assert isinstance(item["stripMolecules"], list)
        for m in item["stripMolecules"]:
            assert "name" in m


def test_never_uses_model_guessed_composition(table, s3fake, monkeypatch):
    # Model guesses paracetamol; photo shows only ecosprin/aspirin words.
    # The guessed molecule must not leak into the result.
    _store_plan(table, _plan(medicines=[_med("m1", "aspirin", 75)]))
    _store_doc(table, keys=["k1.png"])
    words = _words("Ecosprin")
    _mock_vision(monkeypatch, {"k1.png": words},
                 strips_by_key={"k1.png": [
                     {"brandText": "RandomBrand", "compositionText": "Paracetamol (500mg)"}]},
                 lookup=lambda b: [])
    token = auth.issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event({"circleId": "ci_1", "planId": "pl_1",
                                 "documentId": "doc_1"}, token=token), None)
    items = json.loads(res["body"])["items"]
    for item in items:
        for m in item["stripMolecules"]:
            assert m["name"] != "paracetamol"


def test_boxcheck_client_error_is_extraction_failed(monkeypatch):
    from botocore.exceptions import ClientError
    import pytest
    from api import boxcheck_api
    from api.extract import ExtractionFailed

    def boom(key):
        raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "x"}}, "GetObject")
    monkeypatch.setattr(boxcheck_api, "textract_words", boom)
    monkeypatch.setattr(boxcheck_api.plans, "_load", lambda c, p: object())
    monkeypatch.setattr(boxcheck_api, "principal_from_event", lambda e: {"sub": "u", "circleId": "ci_1"})
    monkeypatch.setattr(boxcheck_api, "require", lambda *a, **k: None)

    class T:
        def get_item(self, Key):
            return {"Item": {"keys": ["circles/ci_1/doc_1/p1.jpg"]}}
    monkeypatch.setattr(boxcheck_api._ddb, "Table", lambda name: T())
    with pytest.raises(ExtractionFailed, match="NoSuchKey"):
        boxcheck_api.boxcheck({"body": '{"planId":"pl_1","documentId":"doc_1"}'}, {})
