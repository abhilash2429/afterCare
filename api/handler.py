import json
import os

from api.auth import AuthUnavailable, Unauthorized

ROUTES = {}


def route(method, path):
    def deco(fn):
        ROUTES[(method.upper(), path)] = fn
        return fn
    return deco


def _match(method, path):
    if (method, path) in ROUTES:
        return ROUTES[(method, path)], {}
    parts = path.strip("/").split("/")
    for (m, pattern), fn in ROUTES.items():
        if m != method:
            continue
        pparts = pattern.strip("/").split("/")
        if len(pparts) != len(parts):
            continue
        params = {}
        for want, got in zip(pparts, parts):
            if want.startswith("{") and want.endswith("}"):
                params[want[1:-1]] = got
            elif want != got:
                break
        else:
            return fn, params
    return None, {}


def respond(status, body):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


@route("GET", "/health")
def health(event, params):
    return respond(200, {"ok": True, "commit": os.environ.get("GIT_SHA", "dev")})


def lambda_handler(event, context):
    ctx = event.get("requestContext", {}).get("http", {})
    method = ctx.get("method", "GET").upper()
    path = ctx.get("path", "/")
    fn, params = _match(method, path)
    if fn is None:
        return respond(404, {"code": "not_found", "message": "no route"})
    try:
        return fn(event, params)
    except AuthUnavailable:
        return respond(503, {"code": "auth_unavailable", "message": "sign-in check unavailable"})
    except Unauthorized as exc:
        return respond(401, {"code": "unauthorized", "message": str(exc)})
    except PermissionError as exc:
        return respond(403, {"code": "forbidden", "message": str(exc)})
    except ValueError as exc:
        return respond(422, {"code": "validation_failed", "message": str(exc)})


import api.circles  # noqa: E402,F401
import api.boxcheck_api  # noqa: E402,F401
import api.notify  # noqa: E402,F401
import api.plans  # noqa: E402,F401
import api.speech  # noqa: E402,F401
