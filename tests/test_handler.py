import json

from api.handler import lambda_handler


def _event(method, path):
    return {"requestContext": {"http": {"method": method, "path": path}}}


def test_health_returns_ok():
    res = lambda_handler(_event("GET", "/health"), None)
    assert res["statusCode"] == 200 and json.loads(res["body"])["ok"] is True


def test_unknown_route_is_404():
    assert lambda_handler(_event("GET", "/nope"), None)["statusCode"] == 404


def test_path_params_are_extracted():
    from api.handler import route, respond, _match
    route("GET", "/plans/{planId}")(lambda e, p: respond(200, p))
    fn, params = _match("GET", "/plans/pl_123")
    assert params == {"planId": "pl_123"}


def test_no_access_control_header_on_response():
    res = lambda_handler(_event("GET", "/health"), None)
    assert not any(k.lower().startswith("access-control") for k in res["headers"])
