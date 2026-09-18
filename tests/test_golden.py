"""Extraction accuracy gate. Needs AWS credentials and uploaded photos.

Run: DOCS_BUCKET=<bucket> GOLDEN_S3_PREFIX=circles/ci_demo/golden \
     python -m pytest tests/test_golden.py -m golden -v -s
"""
import glob
import json
import os

import pytest

from api.drugs import normalise_brand, normalise_molecule

pytestmark = pytest.mark.golden

FIELDS = ["name", "strength", "slots", "food", "duration"]
GATES = {"name": 0.90, "strength": 0.90, "slots": 0.80, "food": 0.80, "duration": 0.80}


def _first_molecule(mols):
    if not mols:
        return None, None
    m = mols[0]
    if isinstance(m, dict):
        return normalise_molecule(m["name"]), m["strengthMg"]
    return normalise_molecule(m.name), m.strengthMg


def _score_case(expected, plan):
    got = {normalise_brand(m.brand): m for m in plan.medicines if m.brand}
    hits = {f: 0 for f in FIELDS}
    total = len(expected["medicines"])
    for exp in expected["medicines"]:
        exp_name, exp_strength = _first_molecule(exp["molecules"])
        cand = got.get(normalise_brand(exp["brand"]))
        if cand is None:
            cand = next((m for m in plan.medicines
                         if _first_molecule(m.molecules)[0] == exp_name), None)
        if cand is None:
            continue
        name, strength = _first_molecule(cand.molecules)
        if name is not None and name == exp_name:
            hits["name"] += 1
        if name is not None and (strength == exp_strength or (
                strength is not None and exp_strength is not None
                and abs(strength - exp_strength) < 1e-6)):
            hits["strength"] += 1
        if sorted(cand.slots) == sorted(exp["slots"]):
            hits["slots"] += 1
        if cand.foodRelation == exp["foodRelation"]:
            hits["food"] += 1
        if cand.durationDays == exp["durationDays"]:
            hits["duration"] += 1
    return hits, total


def run_gate(prefix, model_id=None):
    """Returns (accuracy per field, [(caseId, hits, total)])."""
    from api.extract import extract_plan
    totals, counts, rows = {f: 0 for f in FIELDS}, 0, []
    for path in sorted(glob.glob("data/golden/*.json")):
        expected = json.load(open(path, encoding="utf-8"))
        plan = extract_plan(["%s/%s.png" % (prefix, expected["caseId"])], "ci_test",
                            model_id=model_id)
        hits, total = _score_case(expected, plan)
        counts += total
        for f in FIELDS:
            totals[f] += hits[f]
        rows.append((expected["caseId"], hits, total))
    return {f: totals[f] / counts if counts else 0.0 for f in FIELDS}, rows


def test_extraction_meets_the_gate():
    from infra.config import BEDROCK_MODEL_ID
    acc, rows = run_gate(os.environ["GOLDEN_S3_PREFIX"], model_id=BEDROCK_MODEL_ID)
    for case_id, hits, total in rows:
        print(case_id, {f: "%d/%d" % (hits[f], total) for f in FIELDS})
    failures = []
    for f in FIELDS:
        print("ACCURACY %-9s %.2f (gate %.2f)" % (f, acc[f], GATES[f]))
        if acc[f] < GATES[f]:
            failures.append("%s %.2f < %.2f" % (f, acc[f], GATES[f]))
    assert not failures, failures
