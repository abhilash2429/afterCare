from api.models import Plan, Medicine, Molecule, RedFlags


def test_plan_round_trip_preserves_molecules():
    p = Plan(planId="pl_1", circleId="ci_1",
             medicines=[Medicine(lineId="m1", rawText="T. Ecosprin 75 OD",
                                 molecules=[Molecule(name="Aspirin", strengthMg=75)])],
             redFlags=RedFlags(source="generic", text="x"))
    back = Plan.from_dict(p.to_dict())
    assert back.medicines[0].molecules[0].strengthMg == 75
    assert back.redFlags.source == "generic"


def test_plan_round_trip_preserves_medicine_crop():
    p = Plan(planId="pl_1", circleId="ci_1",
             medicines=[Medicine(lineId="m1", rawText="T. Ecosprin 75 OD",
                                 crop={"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.05})])
    back = Plan.from_dict(p.to_dict())
    assert back.medicines[0].crop == {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.05}
