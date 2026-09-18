import base64
import hashlib
import hmac
import json
import time

import boto3
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from moto import mock_aws

import api.auth as auth
from api.auth import issue_circle_token, require, verify_circle_token
from api.handler import ROUTES, lambda_handler

SECRET = "test-secret-that-is-at-least-32-bytes-long"
POOL = "ap-south-1_TESTPOOL"
CLIENT = "testclient123"
ISS = "https://cognito-idp.ap-south-1.amazonaws.com/%s" % POOL
RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setattr(auth, "_secret", lambda: SECRET)
    monkeypatch.setenv("USER_POOL_ID", POOL)
    monkeypatch.setenv("USER_POOL_CLIENT_ID", CLIENT)
    monkeypatch.setenv("WEB_ORIGIN", "https://app.example.com")
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(RSA_KEY.public_key()))
    jwk.update({"kid": "k1", "alg": "RS256", "use": "sig"})
    monkeypatch.setattr(auth, "_jwks_cache", {"keys": [jwk]})


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


def _id_token(**over):
    claims = {"sub": "u-owner", "iss": ISS, "aud": CLIENT, "token_use": "id",
              "exp": int(time.time()) + 300, "iat": int(time.time())}
    claims.update(over)
    return jwt.encode(claims, RSA_KEY, algorithm="RS256", headers={"kid": "k1"})


def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _hs256_by_hand(claims, key_bytes, kid="k1"):
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": kid}).encode())
    body = _b64(json.dumps(claims).encode())
    sig = hmac.new(key_bytes, ("%s.%s" % (head, body)).encode(), hashlib.sha256).digest()
    return "%s.%s.%s" % (head, body, _b64(sig))


def _event(method, path, token=None, body=None):
    e = {"requestContext": {"http": {"method": method, "path": path}}, "headers": {}}
    if token:
        e["headers"]["authorization"] = "Bearer %s" % token
    if body is not None:
        e["body"] = json.dumps(body)
    return e


def _make_owner(table, circle_id="ci_1", sub="u-owner"):
    table.put_item(Item={"PK": "CIRCLE#%s" % circle_id, "SK": "MEMBER#%s" % sub,
                         "role": "owner"})


# circle tokens

def test_round_trip_carries_circle_and_role():
    claims = verify_circle_token(issue_circle_token("ci_1", "caregiver"))
    assert claims["circleId"] == "ci_1" and claims["role"] == "caregiver"
    assert claims["sub"]


def test_circle_token_lasts_90_days():
    claims = verify_circle_token(issue_circle_token("ci_1", "caregiver"))
    assert abs(claims["exp"] - time.time() - 90 * 24 * 3600) < 60


def test_expired_token_is_rejected():
    token = issue_circle_token("ci_1", "caregiver", ttl_seconds=-1)
    with pytest.raises(PermissionError):
        verify_circle_token(token)


def test_tampered_token_is_rejected():
    token = issue_circle_token("ci_1", "caregiver")
    with pytest.raises(PermissionError):
        verify_circle_token(token[:-2] + ("xx" if not token.endswith("xx") else "yy"))


def test_circle_token_cannot_carry_owner_role():
    with pytest.raises(PermissionError):
        verify_circle_token(issue_circle_token("ci_1", "owner"))


def test_alg_none_circle_token_is_rejected():
    token = jwt.encode({"circleId": "ci_1", "role": "caregiver", "iss": "aftercare",
                        "sub": "cg", "exp": int(time.time()) + 60}, None, algorithm="none")
    with pytest.raises(PermissionError):
        verify_circle_token(token)


# algorithm confusion

def test_hs256_token_signed_with_cognito_public_key_is_rejected():
    pem = RSA_KEY.public_key().public_bytes(serialization.Encoding.PEM,
                                            serialization.PublicFormat.SubjectPublicKeyInfo)
    claims = {"sub": "attacker", "iss": ISS, "aud": CLIENT, "token_use": "id",
              "exp": int(time.time()) + 300}
    forged = _hs256_by_hand(claims, pem)
    with pytest.raises(PermissionError):
        auth.principal_from_event(_event("GET", "/x", forged))
    with pytest.raises(PermissionError):
        auth._cognito_claims(forged, jwt.get_unverified_header(forged))


def test_rs256_token_is_never_accepted_as_circle_token():
    token = jwt.encode({"circleId": "ci_1", "role": "caregiver", "iss": "aftercare",
                        "sub": "cg", "exp": int(time.time()) + 60},
                       RSA_KEY, algorithm="RS256", headers={"kid": "k1"})
    with pytest.raises(PermissionError):
        verify_circle_token(token)
    with pytest.raises(PermissionError):
        auth.principal_from_event(_event("GET", "/x", token))


# cognito id tokens

def test_valid_cognito_id_token_is_owner():
    p = auth.principal_from_event(_event("GET", "/x", _id_token()))
    assert p == {"sub": "u-owner", "circleId": None, "role": "owner"}


@pytest.mark.parametrize("override", [
    {"token_use": "access"}, {"aud": "someone-else"},
    {"iss": "https://cognito-idp.ap-south-1.amazonaws.com/other"},
    {"exp": int(time.time()) - 10},
])
def test_bad_cognito_claims_are_rejected(override):
    with pytest.raises(auth.Unauthorized):
        auth.principal_from_event(_event("GET", "/x", _id_token(**override)))


def test_unknown_kid_is_rejected():
    token = jwt.encode({"sub": "u", "iss": ISS, "aud": CLIENT, "token_use": "id",
                        "exp": int(time.time()) + 60}, RSA_KEY, algorithm="RS256",
                       headers={"kid": "other"})
    with pytest.raises(auth.Unauthorized):
        auth.principal_from_event(_event("GET", "/x", token))


def test_missing_token_is_unauthorized():
    with pytest.raises(auth.Unauthorized):
        auth.principal_from_event(_event("GET", "/x"))


def test_caregiver_principal_from_circle_token():
    p = auth.principal_from_event(_event("GET", "/x", issue_circle_token("ci_1", "caregiver")))
    assert p["circleId"] == "ci_1" and p["role"] == "caregiver" and p["sub"]


# require

def test_caregiver_cannot_edit_plans():
    with pytest.raises(PermissionError):
        require({"sub": "cg", "role": "caregiver", "circleId": "ci_1"}, "ci_1", roles=("owner",))


def test_principal_from_another_circle_is_rejected():
    with pytest.raises(PermissionError):
        require({"sub": "cg", "role": "owner", "circleId": "ci_2"}, "ci_1", roles=("owner",))


def test_owner_without_membership_is_rejected(table):
    with pytest.raises(PermissionError):
        require({"sub": "u-owner", "role": "owner", "circleId": None}, "ci_1")


def test_owner_with_membership_is_allowed(table):
    _make_owner(table)
    p = {"sub": "u-owner", "role": "owner", "circleId": None}
    assert require(p, "ci_1", roles=("owner",)) is p


def test_caregiver_token_for_circle_a_is_403_on_circle_b(monkeypatch):
    def fn(event, params):
        require(auth.principal_from_event(event), params["circleId"])
        return {"statusCode": 200, "headers": {}, "body": "{}"}

    monkeypatch.setitem(ROUTES, ("GET", "/__t/{circleId}"), fn)
    token = issue_circle_token("ci_A", "caregiver")
    assert lambda_handler(_event("GET", "/__t/ci_B", token), None)["statusCode"] == 403
    assert lambda_handler(_event("GET", "/__t/ci_A", token), None)["statusCode"] == 200
    assert lambda_handler(_event("GET", "/__t/ci_A"), None)["statusCode"] == 401


# secret loading

def test_secret_is_fetched_once_per_container(monkeypatch):
    monkeypatch.undo()
    calls = []

    class FakeSM:
        def get_secret_value(self, SecretId):
            calls.append(SecretId)
            return {"SecretString": SECRET}

    monkeypatch.setenv("CIRCLE_SECRET_ARN", "arn:aws:secretsmanager:ap-south-1:1:secret:x")
    monkeypatch.setattr(auth, "_secret_cache", None)
    monkeypatch.setattr(auth.boto3, "client", lambda *a, **k: FakeSM())
    assert auth._secret() == SECRET and auth._secret() == SECRET
    assert calls == ["arn:aws:secretsmanager:ap-south-1:1:secret:x"]


# invite + join routes

def test_owner_creates_invite(table):
    _make_owner(table)
    res = lambda_handler(_event("POST", "/circles/ci_1/invite", _id_token()), None)
    body = json.loads(res["body"])
    assert res["statusCode"] == 201
    assert set(body) >= {"token", "url", "expiresAt"}
    assert body["url"].startswith("https://") and body["token"] in body["url"]
    assert "T" in body["expiresAt"]
    item = table.get_item(Key={"PK": "INVITE#%s" % body["token"], "SK": "META"})["Item"]
    assert item["circleId"] == "ci_1" and int(item["expiresAt"]) > time.time()


def test_caregiver_cannot_create_invite(table):
    token = issue_circle_token("ci_1", "caregiver")
    res = lambda_handler(_event("POST", "/circles/ci_1/invite", token), None)
    assert res["statusCode"] == 403


def test_non_member_owner_cannot_create_invite(table):
    res = lambda_handler(_event("POST", "/circles/ci_1/invite", _id_token()), None)
    assert res["statusCode"] == 403


def _invite(table):
    _make_owner(table)
    res = lambda_handler(_event("POST", "/circles/ci_1/invite", _id_token()), None)
    return json.loads(res["body"])["token"]


def test_join_exchanges_invite_once(table):
    invite = _invite(table)
    res = lambda_handler(_event("POST", "/circles/ci_1/join", body={"token": invite}), None)
    body = json.loads(res["body"])
    assert res["statusCode"] == 200
    assert body["role"] == "caregiver" and body["circleId"] == "ci_1"
    claims = verify_circle_token(body["sessionToken"])
    assert claims["circleId"] == "ci_1"
    member = table.get_item(Key={"PK": "CIRCLE#ci_1", "SK": "MEMBER#%s" % claims["sub"]})
    assert member["Item"]["role"] == "caregiver"
    again = lambda_handler(_event("POST", "/circles/ci_1/join", body={"token": invite}), None)
    assert again["statusCode"] == 404


def test_join_with_invite_for_another_circle_is_404(table):
    invite = _invite(table)
    res = lambda_handler(_event("POST", "/circles/ci_2/join", body={"token": invite}), None)
    assert res["statusCode"] == 404


def test_join_with_expired_invite_is_404(table):
    table.put_item(Item={"PK": "INVITE#old", "SK": "META", "circleId": "ci_1",
                         "role": "caregiver", "expiresAt": int(time.time()) - 1,
                         "used": False})
    res = lambda_handler(_event("POST", "/circles/ci_1/join", body={"token": "old"}), None)
    assert res["statusCode"] == 404


@pytest.mark.parametrize("body", [{}, {"token": ""}, {"token": 5}])
def test_join_without_token_is_422(table, body):
    res = lambda_handler(_event("POST", "/circles/ci_1/join", body=body), None)
    assert res["statusCode"] == 422


def test_responses_carry_no_cors_headers(table):
    invite = _invite(table)
    res = lambda_handler(_event("POST", "/circles/ci_1/join", body={"token": invite}), None)
    assert not any(k.lower().startswith("access-control") for k in res["headers"])
