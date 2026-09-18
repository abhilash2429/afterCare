import json

from api.handler import ROUTES, lambda_handler, respond


def _event(method, path):
    return {"requestContext": {"http": {"method": method, "path": path}}}


def test_health_returns_ok():
    res = lambda_handler(_event("GET", "/health"), None)
    assert res["statusCode"] == 200 and json.loads(res["body"])["ok"] is True


def test_unknown_route_is_404():
    assert lambda_handler(_event("GET", "/nope"), None)["statusCode"] == 404


def test_path_params_are_extracted(monkeypatch):
    from api.handler import _match

    def fn(e, p):
        return respond(200, p)

    monkeypatch.setitem(ROUTES, ("GET", "/__t/{id}"), fn)
    matched_fn, params = _match("GET", "/__t/pl_123")
    assert matched_fn is fn
    assert params == {"id": "pl_123"}


def test_no_access_control_header_on_response():
    res = lambda_handler(_event("GET", "/health"), None)
    assert not any(k.lower().startswith("access-control") for k in res["headers"])


def test_permission_error_returns_403(monkeypatch):
    def fn(e, p):
        raise PermissionError("nope")

    monkeypatch.setitem(ROUTES, ("GET", "/__t/forbidden"), fn)
    res = lambda_handler(_event("GET", "/__t/forbidden"), None)
    assert res["statusCode"] == 403
    assert json.loads(res["body"])["code"] == "forbidden"


def test_value_error_returns_422(monkeypatch):
    def fn(e, p):
        raise ValueError("bad")

    monkeypatch.setitem(ROUTES, ("GET", "/__t/invalid"), fn)
    res = lambda_handler(_event("GET", "/__t/invalid"), None)
    assert res["statusCode"] == 422
    assert json.loads(res["body"])["code"] == "validation_failed"
