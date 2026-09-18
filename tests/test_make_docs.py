import glob
import importlib.util
import json
import os

import pytest

from api.frequency import parse_frequency

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
_spec = importlib.util.spec_from_file_location("make_docs", os.path.join(DATA, "make_docs.py"))
make_docs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(make_docs)

FIXTURES = sorted(glob.glob(os.path.join(DATA, "fixtures", "*.json")))


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _golden(case_id):
    return make_docs.expected(_load(os.path.join(DATA, "fixtures", case_id + ".json")))


def test_ten_fixtures():
    assert [os.path.basename(p) for p in FIXTURES] == ["case%02d.json" % i for i in range(1, 11)]


@pytest.mark.parametrize("path", FIXTURES, ids=os.path.basename)
def test_golden_shape(path):
    fx = _load(path)
    g = make_docs.expected(fx)
    assert g["caseId"] == os.path.basename(path)[:-5]
    assert [m["lineId"] for m in g["medicines"]] == ["m%d" % i for i in range(1, len(g["medicines"]) + 1)]
    for m in g["medicines"]:
        assert m["slots"] == parse_frequency(m["frequency"])[0]
        if m["prn"]:
            assert m["slots"] == []
        elif fx["caseId"] != "case10":
            assert m["slots"], "unparseable frequency outside case10: %r" % m["frequency"]
    assert g["redFlags"]["text"]
    assert g["followUp"]["date"] and g["followUp"]["with"]


def test_case01_duplicate_pantoprazole():
    names = [mol["name"] for m in _golden("case01")["medicines"] for mol in m["molecules"]]
    assert names.count("pantoprazole") == 2


def test_case10_missing_duration_and_strength():
    meds = _golden("case10")["medicines"]
    assert any(m["durationDays"] is None for m in meds)
    assert any(mol["strengthMg"] is None for m in meds for mol in m["molecules"])


def test_render_escapes_html():
    fx = _load(os.path.join(DATA, "fixtures", "case01.json"))
    fx["medicines"][0]["raw"] = "T. X <5 mg> & more"
    html = make_docs.render(fx)
    assert "T. X &lt;5 mg&gt; &amp; more" in html
    assert "<5 mg>" not in html
