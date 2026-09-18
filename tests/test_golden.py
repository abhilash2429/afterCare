"""Extraction accuracy gate. Needs AWS credentials and uploaded photos.

Run: DOCS_BUCKET=<bucket> GOLDEN_S3_PREFIX=circles/ci_demo/golden \
     python -m pytest tests/test_golden.py -m golden -v -s
"""
import glob
import json
import os

import pytest

from api.drugs import normalise_brand, normalise_molecule

FIELDS = ["name", "strength", "slots", "food", "duration"]
GATES = {"name": 0.90, "strength": 0.90, "slots": 0.80, "food": 0.80, "duration": 0.80}


def _first_molecule(mols):
    if not mols:
        return None, None
    m = mols[0]
    if isinstance(m, dict):
        return normalise_molecule(m["name"]), m["strengthMg"]
    return normalise_molecule(m.name), m.strengthMg


def _molecule_map(mols):
    """{normalised name: strengthMg}, over every molecule on the line, not just the first."""
    out = {}
    for m in mols or []:
        if isinstance(m, dict):
            out[normalise_molecule(m["name"])] = m["strengthMg"]
        else:
            out[normalise_molecule(m.name)] = m.strengthMg
    return out


def _score_case(expected, plan):
    """Returns (hits, total, trusted_hits, trusted_total, needs_confirmation, line_count).

    A name hit requires the full set of molecules on the line to match (not just the
    first). A strength hit additionally requires every one of those molecules to have a
    known, equal strength - so a wrong name with two coincidentally-None strengths is
    never a strength hit. Extra lines the model produced that match no expected line are
    misses too: they inflate `total` with nothing to show for it.
    """
    got = {normalise_brand(m.brand): m for m in plan.medicines if m.brand}
    hits = {f: 0 for f in FIELDS}
    trusted_hits = {f: 0 for f in FIELDS}
    matched, trusted_total = set(), 0
    for exp in expected["medicines"]:
        exp_map = _molecule_map(exp["molecules"])
        exp_name, _ = _first_molecule(exp["molecules"])
        cand = got.get(normalise_brand(exp["brand"]))
        cand_idx = plan.medicines.index(cand) if cand is not None else None
        if cand is None:
            for i, m in enumerate(plan.medicines):
                if i in matched:
                    continue
                if any(normalise_molecule(x.name) == exp_name for x in m.molecules):
                    cand, cand_idx = m, i
                    break
        if cand is None:
            continue
        matched.add(cand_idx)

        line_hits = {f: 0 for f in FIELDS}
        cand_map = _molecule_map(cand.molecules)
        if exp_map and set(cand_map) == set(exp_map):
            line_hits["name"] = 1
            if all(cand_map[n] is not None and exp_map[n] is not None
                   and abs(cand_map[n] - exp_map[n]) < 1e-6 for n in exp_map):
                line_hits["strength"] = 1
        if sorted(cand.slots) == sorted(exp["slots"]):
            line_hits["slots"] = 1
        if cand.foodRelation == exp["foodRelation"]:
            line_hits["food"] = 1
        if cand.durationDays == exp["durationDays"]:
            line_hits["duration"] = 1

        for f in FIELDS:
            hits[f] += line_hits[f]
        if not cand.needsConfirmation:
            trusted_total += 1
            for f in FIELDS:
                trusted_hits[f] += line_hits[f]

    extra = len(plan.medicines) - len(matched)
    total = len(expected["medicines"]) + max(0, extra)
    needs_confirmation = sum(1 for m in plan.medicines if m.needsConfirmation)
    return hits, total, trusted_hits, trusted_total, needs_confirmation, len(plan.medicines)


def run_gate(prefix, model_id=None):
    """Returns (accuracy per field, [(caseId, hits, total)], trusted accuracy per field,
    needsConfirmation rate)."""
    from api.extract import extract_plan
    totals, counts, rows = {f: 0 for f in FIELDS}, 0, []
    trusted_totals, trusted_counts = {f: 0 for f in FIELDS}, 0
    confirmed_lines, all_lines = 0, 0
    for path in sorted(glob.glob("data/golden/*.json")):
        expected = json.load(open(path, encoding="utf-8"))
        plan = extract_plan(["%s/%s.png" % (prefix, expected["caseId"])], "ci_test",
                            model_id=model_id)
        hits, total, t_hits, t_total, confirmed, n_lines = _score_case(expected, plan)
        counts += total
        confirmed_lines += confirmed
        all_lines += n_lines
        trusted_counts += t_total
        for f in FIELDS:
            totals[f] += hits[f]
            trusted_totals[f] += t_hits[f]
        rows.append((expected["caseId"], hits, total))
    acc = {f: totals[f] / counts if counts else 0.0 for f in FIELDS}
    trusted_acc = {f: trusted_totals[f] / trusted_counts if trusted_counts else 0.0
                   for f in FIELDS}
    needs_confirmation_rate = confirmed_lines / all_lines if all_lines else 0.0
    return acc, rows, trusted_acc, needs_confirmation_rate


def _plan(medicines):
    from api.models import Plan
    return Plan(planId="p1", circleId="c1", medicines=medicines)


def _medicine(brand, mols, slots=(), food="unspecified", duration=None, confirm=False):
    from api.models import Medicine, Molecule
    return Medicine(lineId="m", rawText="", brand=brand,
                    molecules=[Molecule(*mm) for mm in mols], slots=list(slots),
                    foodRelation=food, durationDays=duration, needsConfirmation=confirm)


# I5: a name hit needs every molecule to match, a wrong name is never a strength hit even
# when both strengths happen to be None, and a line the model invented is a miss too.
def test_score_case_scores_all_molecules_and_penalises_extra_lines():
    expected = {"medicines": [
        {"brand": "Augmentin", "molecules": [{"name": "Amoxycillin", "strengthMg": 400},
                                             {"name": "Clavulanic acid", "strengthMg": 57}],
         "slots": ["morning"], "foodRelation": "after", "durationDays": 5},
        {"brand": "Madeup", "molecules": [{"name": "Madeupzole", "strengthMg": None}],
         "slots": ["night"], "foodRelation": "before", "durationDays": 10},
    ]}
    plan = _plan([
        # Right brand, only one of the two molecules -> not a name hit, not a strength hit.
        _medicine("Augmentin", [("amoxycillin", 400.0, "mg")], slots=["morning"],
                  food="after", duration=5),
        # Wrong name but both strengths are None - must not count as a strength hit.
        # Also mismatched on slots/food/duration so they don't accidentally hit either.
        _medicine("Madeup", [("somethingelse", None, "mg")]),
        # A line with no matching expected entry at all.
        _medicine("Unexpected", [("randomdrug", 10.0, "mg")]),
    ])
    hits, total, _, _, _, n_lines = _score_case(expected, plan)
    assert total == 3  # 2 expected + 1 unmatched extra line
    assert n_lines == 3
    assert hits["name"] == 0
    assert hits["strength"] == 0
    assert hits["slots"] == 1
    assert hits["food"] == 1
    assert hits["duration"] == 1


def test_score_case_splits_trusted_line_accuracy():
    expected = {"medicines": [
        {"brand": "Ecosprin", "molecules": [{"name": "Aspirin", "strengthMg": 75}],
         "slots": ["morning"], "foodRelation": "after", "durationDays": 30},
    ]}
    plan = _plan([_medicine("Ecosprin", [("aspirin", 75.0, "mg")], slots=["morning"],
                            food="after", duration=30, confirm=False)])
    hits, total, trusted_hits, trusted_total, confirmed, n_lines = _score_case(expected, plan)
    assert (hits["name"], total, trusted_hits["name"], trusted_total, confirmed) == \
        (1, 1, 1, 1, 0)


@pytest.mark.golden
def test_extraction_meets_the_gate():
    from infra.config import BEDROCK_MODEL_ID
    acc, rows, trusted_acc, needs_confirmation_rate = run_gate(
        os.environ["GOLDEN_S3_PREFIX"], model_id=BEDROCK_MODEL_ID)
    for case_id, hits, total in rows:
        print(case_id, {f: "%d/%d" % (hits[f], total) for f in FIELDS})
    print("needsConfirmation rate: %.2f" % needs_confirmation_rate)
    for f in FIELDS:
        print("TRUSTED-LINE ACCURACY %-9s %.2f" % (f, trusted_acc[f]))
    failures = []
    for f in FIELDS:
        print("ACCURACY %-9s %.2f (gate %.2f)" % (f, acc[f], GATES[f]))
        if acc[f] < GATES[f]:
            failures.append("%s %.2f < %.2f" % (f, acc[f], GATES[f]))
    assert not failures, failures
