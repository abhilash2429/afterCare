import json
import os
import time
import urllib.request

import boto3
import jwt

from api.common import REGION, TABLE, new_id

CIRCLE_ISSUER = "aftercare"
CIRCLE_TTL = 90 * 24 * 3600

_secret_cache = None
_jwks_cache = None
_table_cache = None


class Unauthorized(PermissionError):
    """Missing or invalid credentials (401), as opposed to a denied role (403)."""

    def __init__(self):
        super().__init__("invalid token")


class AuthUnavailable(Exception):
    """The Cognito JWKS could not be fetched (503)."""


def _secret():
    global _secret_cache
    if _secret_cache is None:
        _secret_cache = boto3.client("secretsmanager", region_name=REGION).get_secret_value(
            SecretId=os.environ["CIRCLE_SECRET_ARN"])["SecretString"]
    return _secret_cache


def _table():
    global _table_cache
    if _table_cache is None:
        _table_cache = boto3.resource("dynamodb", region_name=REGION).Table(TABLE)
    return _table_cache


def _jwks(pool_id):
    global _jwks_cache
    if _jwks_cache is None:
        url = "https://cognito-idp.%s.amazonaws.com/%s/.well-known/jwks.json" % (REGION, pool_id)
        try:
            with urllib.request.urlopen(url, timeout=5) as res:
                keys = json.loads(res.read())["keys"]
        except (OSError, ValueError, KeyError, TypeError):
            raise AuthUnavailable() from None
        _jwks_cache = {"keys": keys}
    return _jwks_cache


def issue_circle_token(circle_id, role, ttl_seconds=CIRCLE_TTL, sub=None):
    now = int(time.time())
    payload = {"sub": sub or new_id("cg"), "circleId": circle_id, "role": role,
               "iss": CIRCLE_ISSUER, "iat": now, "exp": now + ttl_seconds}
    return jwt.encode(payload, _secret(), algorithm="HS256")


def verify_circle_token(token):
    try:
        claims = jwt.decode(token, _secret(), algorithms=["HS256"], issuer=CIRCLE_ISSUER,
                            options={"require": ["exp", "iss", "sub"]})
    except jwt.PyJWTError:
        raise Unauthorized() from None
    if claims.get("role") != "caregiver" or not claims.get("circleId"):
        raise Unauthorized()
    return claims


def _cognito_claims(token, header):
    pool_id = os.environ["USER_POOL_ID"]
    key = next((k for k in _jwks(pool_id)["keys"] if k.get("kid") == header.get("kid")), None)
    if key is None:
        raise Unauthorized()
    # ponytail: no JWKS refetch on unknown kid; Cognito does not rotate pool keys. Add a
    # rate-limited refetch if that ever changes.
    try:
        claims = jwt.decode(
            token, jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key)), algorithms=["RS256"],
            audience=os.environ["USER_POOL_CLIENT_ID"],
            issuer="https://cognito-idp.%s.amazonaws.com/%s" % (REGION, pool_id),
            options={"require": ["exp", "iss", "aud", "sub", "token_use"]})
    except jwt.PyJWTError:
        raise Unauthorized() from None
    if claims["token_use"] != "id":
        raise Unauthorized()
    return claims


def principal_from_event(event):
    header = (event.get("headers") or {}).get("authorization", "")
    token = header[7:].strip() if header.lower().startswith("bearer ") else ""
    if not token:
        raise Unauthorized()
    try:
        jwt_header = jwt.get_unverified_header(token)
    except jwt.PyJWTError:
        raise Unauthorized() from None
    # The unverified alg only picks the verifier; each verifier pins its own algorithm and key.
    alg = jwt_header.get("alg")
    if alg == "RS256":
        claims = _cognito_claims(token, jwt_header)
        return {"sub": claims["sub"], "circleId": None, "role": "owner",
                "email": claims.get("email")}
    if alg == "HS256":
        claims = verify_circle_token(token)
        return {"sub": claims["sub"], "circleId": claims["circleId"], "role": claims["role"]}
    raise Unauthorized()


def require(principal, circle_id, roles=("owner", "caregiver")):
    if principal.get("role") not in roles:
        raise PermissionError("role not permitted")
    if principal.get("circleId") is not None:
        if principal["circleId"] != circle_id:
            raise PermissionError("token is not for this circle")
        return principal
    # A Cognito login proves identity only; ownership of this circle must be on record.
    item = _table().get_item(Key={"PK": "CIRCLE#%s" % circle_id,
                                  "SK": "MEMBER#%s" % principal["sub"]}).get("Item")
    if not item or item.get("role") != "owner":
        raise PermissionError("not a member of this circle")
    return principal
