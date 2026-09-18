from api.models import Medicine, Molecule
from api.boxcheck import check_box, Strip


def med(line_id, name, strength, brand=None):
    return Medicine(lineId=line_id, rawText="", brand=brand,
                    molecules=[Molecule(name, strength)], frequency="OD",
                    slots=["morning"], confidence=0.95, sourceBlockIds=["b1"],
                    needsConfirmation=False)


def verdicts(items):
    return {(i["prescribedLineId"], i["verdict"], i["reason"]) for i in items}


def test_same_molecule_different_brand_is_matched():
    items = check_box([med("m1", "aspirin", 75, "Ecosprin")],
                      [Strip("Delisprin 75", [Molecule("aspirin", 75)])])
    assert ("m1", "matched", "exact_match") in verdicts(items)


def test_strength_mismatch_is_amber():
    items = check_box([med("m1", "aspirin", 75)],
                      [Strip("Ecosprin 150", [Molecule("aspirin", 150)])])
    assert ("m1", "check", "strength_mismatch") in verdicts(items)


def test_combination_strip_containing_the_molecule_is_amber():
    items = check_box([med("m1", "aspirin", 75)],
                      [Strip("Ecosprin AV", [Molecule("aspirin", 75),
                                             Molecule("atorvastatin", 20)])])
    assert ("m1", "check", "combination_extra") in verdicts(items)


def test_missing_medicine_is_red():
    items = check_box([med("m1", "aspirin", 75), med("m2", "pantoprazole", 40)],
                      [Strip("Ecosprin 75", [Molecule("aspirin", 75)])])
    assert ("m2", "do_not_take", "missing_from_box") in verdicts(items)


def test_extra_strip_is_red_and_has_no_line_id():
    items = check_box([med("m1", "aspirin", 75)],
                      [Strip("Ecosprin 75", [Molecule("aspirin", 75)]),
                       Strip("Alprax 0.5", [Molecule("alprazolam", 0.5)])])
    assert (None, "do_not_take", "not_prescribed") in verdicts(items)


def test_duplicate_molecule_across_two_prescribed_brands_is_red():
    items = check_box([med("m1", "pantoprazole", 40, "Pan 40"),
                       med("m2", "pantoprazole", 40, "Pantocid 40")],
                      [Strip("Pan 40", [Molecule("pantoprazole", 40)]),
                       Strip("Pantocid 40", [Molecule("pantoprazole", 40)])])
    reasons = {i["reason"] for i in items}
    assert "duplicate_molecule" in reasons
    assert any(i["verdict"] == "do_not_take" for i in items if i["reason"] == "duplicate_molecule")


def test_unreadable_brand_with_matching_molecule_is_amber():
    items = check_box([med("m1", "aspirin", 75)],
                      [Strip(None, [Molecule("aspirin", 75)])])
    assert ("m1", "check", "brand_unreadable") in verdicts(items)


def test_no_item_ever_says_safe():
    items = check_box([med("m1", "aspirin", 75)],
                      [Strip("Ecosprin 75", [Molecule("aspirin", 75)])])
    assert all("safe" not in i["message"].lower() for i in items)


# R7 - every message must carry its tier's required phrase, across all 7 reasons.
TIER_PHRASE = {
    "matched": "matches your prescription",
    "check": "check with your chemist",
    "do_not_take": "ask your doctor",
}


def test_all_seven_reasons_carry_their_tier_phrase_and_never_say_safe():
    scenarios = [
        ([med("m1", "aspirin", 75, "Ecosprin")],
         [Strip("Delisprin 75", [Molecule("aspirin", 75)])]),  # exact_match
        ([med("m1", "aspirin", 75)],
         [Strip("Ecosprin 150", [Molecule("aspirin", 150)])]),  # strength_mismatch
        ([med("m1", "aspirin", 75)],
         [Strip("Ecosprin AV", [Molecule("aspirin", 75), Molecule("atorvastatin", 20)])]),  # combination_extra
        ([med("m1", "aspirin", 75)],
         [Strip(None, [Molecule("aspirin", 75)])]),  # brand_unreadable
        ([med("m1", "aspirin", 75), med("m2", "pantoprazole", 40)],
         [Strip("Ecosprin 75", [Molecule("aspirin", 75)])]),  # missing_from_box
        ([med("m1", "aspirin", 75)],
         [Strip("Ecosprin 75", [Molecule("aspirin", 75)]),
          Strip("Alprax 0.5", [Molecule("alprazolam", 0.5)])]),  # not_prescribed
        ([med("m1", "pantoprazole", 40, "Pan 40"), med("m2", "pantoprazole", 40, "Pantocid 40")],
         [Strip("Pan 40", [Molecule("pantoprazole", 40)]),
          Strip("Pantocid 40", [Molecule("pantoprazole", 40)])]),  # duplicate_molecule
    ]

    seen_reasons = set()
    for medicines, strips in scenarios:
        for item in check_box(medicines, strips):
            message = item["message"].lower()
            assert "safe" not in message
            assert TIER_PHRASE[item["verdict"]] in message
            seen_reasons.add(item["reason"])

    assert seen_reasons == {
        "exact_match", "strength_mismatch", "combination_extra", "brand_unreadable",
        "missing_from_box", "not_prescribed", "duplicate_molecule",
    }


def test_unit_mismatch_is_not_matched():
    prescribed = Medicine(lineId="m1", rawText="", brand=None,
                          molecules=[Molecule("vitamin d3", 60000, "iu")], frequency="OD",
                          slots=["morning"], confidence=0.95, sourceBlockIds=["b1"],
                          needsConfirmation=False)
    items = check_box([prescribed],
                      [Strip("Vitamin D3", [Molecule("vitamin d3", 60000, "mg")])])
    m1_verdicts = {i["verdict"] for i in items if i["prescribedLineId"] == "m1"}
    assert "matched" not in m1_verdicts
