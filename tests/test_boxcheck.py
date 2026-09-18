from api.models import Medicine, Molecule
from api.boxcheck import check_box, Strip


def med(line_id, name, strength, brand=None, unit="mg"):
    return Medicine(lineId=line_id, rawText="", brand=brand,
                    molecules=[Molecule(name, strength, unit)], frequency="OD",
                    slots=["morning"], confidence=0.95, sourceBlockIds=["b1"],
                    needsConfirmation=False)


def by_line(items):
    out = {}
    for i in items:
        out.setdefault(i["prescribedLineId"], []).append((i["verdict"], i["reason"]))
    return out


def test_same_molecule_different_brand_is_matched():
    items = check_box([med("m1", "aspirin", 75, "Ecosprin")],
                      [Strip("Delisprin 75", [Molecule("aspirin", 75)])])
    assert by_line(items) == {"m1": [("matched", "exact_match")]}


def test_two_identical_packs_are_both_matched():
    items = check_box([med("m1", "aspirin", 75, "Ecosprin")],
                      [Strip("Ecosprin 75", [Molecule("aspirin", 75)]),
                       Strip("Ecosprin 75", [Molecule("aspirin", 75)])])
    assert by_line(items) == {"m1": [("matched", "exact_match"), ("matched", "exact_match")]}


def test_unreadable_pack_next_to_readable_pack_is_not_flagged_not_prescribed():
    items = check_box([med("m1", "aspirin", 75)],
                      [Strip(None, [Molecule("aspirin", 75)]),
                       Strip("Ecosprin 75", [Molecule("aspirin", 75)])])
    assert by_line(items) == {"m1": [("check", "brand_unreadable"), ("matched", "exact_match")]}


def test_strength_mismatch_is_amber():
    items = check_box([med("m1", "aspirin", 75)],
                      [Strip("Ecosprin 150", [Molecule("aspirin", 150)])])
    assert by_line(items) == {"m1": [("check", "strength_mismatch")]}


def test_combination_strip_with_unprescribed_molecule_is_combination_extra():
    items = check_box([med("m1", "aspirin", 75)],
                      [Strip("Ecosprin AV", [Molecule("aspirin", 75),
                                             Molecule("atorvastatin", 20)])])
    assert by_line(items) == {"m1": [("check", "combination_extra")]}


def test_combination_strip_spanning_two_lines_satisfies_both():
    items = check_box([med("m1", "metformin", 500), med("m2", "glimepiride", 1)],
                      [Strip("Glycomet GP1", [Molecule("metformin", 500),
                                              Molecule("glimepiride", 1)])])
    assert by_line(items) == {"m1": [("check", "combination_strip")],
                              "m2": [("check", "combination_strip")]}


def test_missing_medicine_is_red():
    items = check_box([med("m1", "aspirin", 75), med("m2", "pantoprazole", 40)],
                      [Strip("Ecosprin 75", [Molecule("aspirin", 75)])])
    assert by_line(items) == {"m1": [("matched", "exact_match")],
                              "m2": [("do_not_take", "missing_from_box")]}


def test_extra_strip_is_red_and_has_no_line_id():
    items = check_box([med("m1", "aspirin", 75)],
                      [Strip("Ecosprin 75", [Molecule("aspirin", 75)]),
                       Strip("Alprax 0.5", [Molecule("alprazolam", 0.5)])])
    assert by_line(items) == {"m1": [("matched", "exact_match")],
                              None: [("do_not_take", "not_prescribed")]}


def test_duplicate_molecule_later_line_carries_its_strip():
    items = check_box([med("m1", "pantoprazole", 40, "Pan 40"),
                       med("m2", "pantoprazole", 40, "Pantocid 40")],
                      [Strip("Pan 40", [Molecule("pantoprazole", 40)]),
                       Strip("Pantocid 40", [Molecule("pantoprazole", 40)])])
    assert by_line(items) == {"m1": [("matched", "exact_match")],
                              "m2": [("do_not_take", "duplicate_molecule")]}
    m1, m2 = items
    assert m1["stripBrandText"] == "Pan 40"
    assert m2["stripBrandText"] == "Pantocid 40"
    assert m2["stripMolecules"] == [{"name": "pantoprazole", "strengthMg": 40, "unit": "mg"}]


def test_duplicate_molecule_with_one_strip_is_never_also_missing():
    items = check_box([med("m1", "pantoprazole", 40, "Pan 40"),
                       med("m2", "pantoprazole", 40, "Pantocid 40")],
                      [Strip("Pan 40", [Molecule("pantoprazole", 40)])])
    assert by_line(items) == {"m1": [("matched", "exact_match")],
                              "m2": [("do_not_take", "duplicate_molecule")]}
    assert items[1]["stripBrandText"] is None and items[1]["stripMolecules"] == []


def test_aspirin_75_and_150_lines_with_one_150_strip():
    items = check_box([med("m1", "aspirin", 75), med("m2", "aspirin", 150)],
                      [Strip("Ecosprin 150", [Molecule("aspirin", 150)])])
    assert by_line(items) == {"m1": [("do_not_take", "missing_from_box")],
                              "m2": [("do_not_take", "duplicate_molecule")]}
    assert items[1]["stripBrandText"] == "Ecosprin 150"


def test_exact_matches_resolve_before_fallbacks():
    items = check_box([med("m1", "aspirin", 75), med("m2", "atorvastatin", 10)],
                      [Strip("Ecosprin 150", [Molecule("aspirin", 150)]),
                       Strip("Ecosprin 75", [Molecule("aspirin", 75)]),
                       Strip("Atorva 10", [Molecule("atorvastatin", 10)])])
    assert by_line(items) == {"m1": [("matched", "exact_match"), ("check", "strength_mismatch")],
                              "m2": [("matched", "exact_match")]}


def test_unreadable_brand_with_matching_molecule_is_amber():
    items = check_box([med("m1", "aspirin", 75)],
                      [Strip(None, [Molecule("aspirin", 75)])])
    assert by_line(items) == {"m1": [("check", "brand_unreadable")]}


def test_unit_mismatch_is_not_matched():
    items = check_box([med("m1", "vitamin d3", 60000, unit="iu")],
                      [Strip("Vitamin D3", [Molecule("vitamin d3", 60000, "mg")])])
    assert by_line(items) == {"m1": [("check", "strength_mismatch")]}
    assert items[0]["stripMolecules"] == [{"name": "vitamin d3", "strengthMg": 60000, "unit": "mg"}]


def test_prn_line_participates_like_any_other():
    prn = med("m1", "paracetamol", 650)
    prn.prn = True
    items = check_box([prn], [Strip("Dolo 650", [Molecule("paracetamol", 650)])])
    assert by_line(items) == {"m1": [("matched", "exact_match")]}


def test_no_item_ever_says_safe():
    items = check_box([med("m1", "aspirin", 75)],
                      [Strip("Ecosprin 75", [Molecule("aspirin", 75)])])
    assert all("safe" not in i["message"].lower() for i in items)


# R7 - every message must carry its tier's required phrase, across all reasons.
TIER_PHRASE = {
    "matched": "matches your prescription",
    "check": "check with your chemist",
    "do_not_take": "ask your doctor",
}


def test_all_reasons_carry_their_tier_phrase_and_never_say_safe():
    scenarios = [
        ([med("m1", "aspirin", 75, "Ecosprin")],
         [Strip("Delisprin 75", [Molecule("aspirin", 75)])]),  # exact_match
        ([med("m1", "aspirin", 75)],
         [Strip("Ecosprin 150", [Molecule("aspirin", 150)])]),  # strength_mismatch
        ([med("m1", "aspirin", 75)],
         [Strip("Ecosprin AV", [Molecule("aspirin", 75), Molecule("atorvastatin", 20)])]),  # combination_extra
        ([med("m1", "metformin", 500), med("m2", "glimepiride", 1)],
         [Strip("Glycomet GP1", [Molecule("metformin", 500), Molecule("glimepiride", 1)])]),  # combination_strip
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
        "exact_match", "strength_mismatch", "combination_extra", "combination_strip",
        "brand_unreadable", "missing_from_box", "not_prescribed", "duplicate_molecule",
    }
