from datetime import date

from api.doses import build_doses
from api.models import Plan, Medicine, Molecule


def _plan(meds):
    return Plan(planId="pl_1", circleId="ci_1", medicines=meds)


def _med(line_id, slots, duration=None, prn=False):
    return Medicine(lineId=line_id, rawText="", molecules=[Molecule("x", 1)],
                    frequency="OD", slots=slots, durationDays=duration, prn=prn,
                    confidence=0.95, sourceBlockIds=["b1"], needsConfirmation=False)


def test_one_dose_per_slot_per_day_not_per_medicine():
    doses = build_doses(_plan([_med("m1", ["morning"]), _med("m2", ["morning"])]),
                        date(2026, 9, 20), days=1)
    assert len(doses) == 1
    assert sorted(doses[0].medicineLineIds) == ["m1", "m2"]


def test_bd_creates_two_slots_per_day():
    doses = build_doses(_plan([_med("m1", ["morning", "night"])]), date(2026, 9, 20), days=2)
    assert len(doses) == 4
    assert {d.slot for d in doses} == {"morning", "night"}


def test_prn_medicine_is_never_scheduled():
    doses = build_doses(_plan([_med("m1", [], prn=True)]), date(2026, 9, 20), days=3)
    assert doses == []


def test_duration_shorter_than_window_stops_early():
    doses = build_doses(_plan([_med("m1", ["morning"], duration=2)]), date(2026, 9, 20), days=7)
    assert len(doses) == 2


def test_missing_duration_defaults_to_seven_days():
    doses = build_doses(_plan([_med("m1", ["morning"], duration=None)]), date(2026, 9, 20), days=30)
    assert len(doses) == 7


def test_dose_id_is_stable_and_sortable():
    doses = build_doses(_plan([_med("m1", ["morning"])]), date(2026, 9, 20), days=1)
    assert doses[0].doseId == "ci_1#2026-09-20#morning"
