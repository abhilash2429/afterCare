from api.models import Plan, Medicine, Molecule, RedFlags
from api.validate import validate_plan, validate_edit, can_activate, GENERIC_RED_FLAG_TEXT


def _med(**kw):
    base = dict(lineId="m1", rawText="T. Ecosprin 75 OD", brand="Ecosprin",
                molecules=[Molecule(name="Aspirin", strengthMg=75)], frequency="OD",
                slots=["morning"], confidence=0.95, sourceBlockIds=["b1"],
                needsConfirmation=False)
    base.update(kw)
    return Medicine(**base)


def _plan(**kw):
    base = dict(planId="pl_1", circleId="ci_1", medicines=[_med()],
                redFlags=RedFlags(source="document", text="chest pain", sourceBlockIds=["b9"]))
    base.update(kw)
    return Plan(**base)


def test_valid_plan_has_no_errors():
    assert validate_plan(_plan()) == []


def test_document_red_flags_require_source_blocks():
    p = _plan(redFlags=RedFlags(source="document", text="chest pain", sourceBlockIds=[]))
    assert "redFlags.sourceBlockIds" in " ".join(validate_plan(p))


def test_generic_red_flag_text_must_be_the_constant():
    p = _plan(redFlags=RedFlags(source="generic", text="watch out for anything odd"))
    assert "redFlags.text" in " ".join(validate_plan(p))
    ok = _plan(redFlags=RedFlags(source="generic", text=GENERIC_RED_FLAG_TEXT))
    assert validate_plan(ok) == []


def test_value_without_source_blocks_is_rejected():
    p = _plan(medicines=[_med(sourceBlockIds=[], source="textract")])
    assert "sourceBlockIds" in " ".join(validate_plan(p))


def test_vision_only_medicine_may_have_no_source_blocks():
    p = _plan(medicines=[_med(sourceBlockIds=[], source="vision_only", needsConfirmation=True)])
    assert validate_plan(p) == []


def test_prn_medicine_must_have_no_slots():
    p = _plan(medicines=[_med(prn=True, slots=["morning"])])
    assert "prn" in " ".join(validate_plan(p))


def test_dose_change_without_user_edited_flag_is_rejected():
    original = _plan()
    edited = _plan(medicines=[_med(molecules=[Molecule(name="Aspirin", strengthMg=150)])])
    assert validate_edit(original, edited, user_edited=False) != []
    assert validate_edit(original, edited, user_edited=True) == []


def test_frequency_change_without_user_edited_flag_is_rejected():
    original = _plan()
    edited = _plan(medicines=[_med(frequency="BD", slots=["morning", "night"])])
    assert validate_edit(original, edited, user_edited=False) != []


def test_cannot_activate_while_a_field_needs_confirmation():
    p = _plan(medicines=[_med(needsConfirmation=True)])
    assert can_activate(p) != []
    assert can_activate(_plan()) == []


# --- fix round 1: R10/R11/R12 ---

def test_rename_lineid_without_user_edit_is_rejected():
    original = _plan()
    edited = _plan(medicines=[_med(lineId="m2", molecules=[Molecule(name="Aspirin", strengthMg=150)])])
    assert validate_edit(original, edited, user_edited=False) != []


def test_duplicate_lineids_in_edited_are_rejected_without_user_edit():
    original = _plan()
    edited = _plan(medicines=[
        _med(lineId="m1", molecules=[Molecule(name="Aspirin", strengthMg=150)]),
        _med(lineId="m1", molecules=[Molecule(name="Aspirin", strengthMg=75)]),
    ])
    assert validate_edit(original, edited, user_edited=False) != []


def test_added_line_without_user_edit_is_rejected():
    original = _plan()
    edited = _plan(medicines=[_med(), _med(lineId="m2", sourceBlockIds=["b2"])])
    assert validate_edit(original, edited, user_edited=False) != []


def test_removed_line_without_user_edit_is_rejected():
    original = _plan(medicines=[_med(), _med(lineId="m2", sourceBlockIds=["b2"])])
    edited = _plan(medicines=[_med()])
    assert validate_edit(original, edited, user_edited=False) != []


def test_added_line_allowed_with_user_edited():
    original = _plan()
    edited = _plan(medicines=[_med(), _med(lineId="m2", source="user", sourceBlockIds=[])])
    assert validate_edit(original, edited, user_edited=True) == []


def test_added_line_with_textract_source_is_rejected_even_with_user_edited():
    original = _plan()
    edited = _plan(medicines=[_med(), _med(lineId="m2", sourceBlockIds=["b2"])])
    assert validate_edit(original, edited, user_edited=True) != []


def test_added_user_line_with_source_blocks_is_rejected():
    original = _plan()
    edited = _plan(medicines=[_med(), _med(lineId="m2", source="user",
                                          sourceBlockIds=["b2"])])
    assert validate_edit(original, edited, user_edited=True) != []


def test_user_source_may_have_empty_source_blocks():
    p = _plan(medicines=[_med(), _med(lineId="m2", source="user", sourceBlockIds=[])])
    assert validate_plan(p) == []


def test_duplicate_lineids_rejected_even_with_user_edited():
    original = _plan()
    edited = _plan(medicines=[
        _med(lineId="m1"),
        _med(lineId="m1", sourceBlockIds=["b2"]),
    ])
    assert validate_edit(original, edited, user_edited=True) != []


def test_validate_plan_rejects_duplicate_lineids():
    p = _plan(medicines=[_med(lineId="m1"), _med(lineId="m1", sourceBlockIds=["b2"])])
    assert validate_plan(p) != []


def test_null_frequency_non_prn_requires_confirmation():
    p = _plan(medicines=[_med(frequency=None, slots=[], needsConfirmation=False)])
    assert validate_plan(p) != []


def test_null_frequency_prn_is_fine():
    p = _plan(medicines=[_med(frequency=None, slots=[], prn=True, needsConfirmation=False)])
    assert validate_plan(p) == []


def test_confidence_none_produces_error_not_crash():
    p = _plan(medicines=[_med(confidence=None)])
    errors = validate_plan(p)
    assert errors != []
    assert all(isinstance(e, str) for e in errors)


def test_unknown_slot_is_rejected():
    p = _plan(medicines=[_med(slots=["afternoon"])])
    assert validate_plan(p) != []


def test_can_activate_without_redflags_is_rejected():
    p = _plan(redFlags=None)
    assert can_activate(p) != []


# --- final review: R24 ---

def _rejected_only_without_user_edit(edited):
    original = _plan()
    errors = validate_edit(original, edited, user_edited=False)
    assert any("without userEdited" in e for e in errors), errors
    assert validate_edit(original, edited, user_edited=True) == []


def test_slot_change_without_user_edited_is_rejected():
    _rejected_only_without_user_edit(_plan(medicines=[_med(slots=["night"])]))


def test_prn_flip_without_user_edited_is_rejected():
    _rejected_only_without_user_edit(_plan(medicines=[_med(prn=True, slots=[])]))


def test_unit_change_without_user_edited_is_rejected():
    _rejected_only_without_user_edit(
        _plan(medicines=[_med(molecules=[Molecule(name="Aspirin", strengthMg=75, unit="iu")])]))


def test_duration_change_without_user_edited_is_rejected():
    original = _plan(medicines=[_med(durationDays=30)])
    edited = _plan(medicines=[_med(durationDays=90)])
    assert validate_edit(original, edited, user_edited=False) != []
    assert validate_edit(original, edited, user_edited=True) == []


def test_source_change_without_user_edited_is_rejected():
    _rejected_only_without_user_edit(_plan(medicines=[_med(source="vision_only")]))


def test_source_block_change_without_user_edited_is_rejected():
    _rejected_only_without_user_edit(_plan(medicines=[_med(sourceBlockIds=["b7"])]))


def test_cosmetic_name_edit_is_not_a_dose_change():
    edited = _plan(medicines=[_med(molecules=[Molecule(name="Aspirin IP", strengthMg=75.0)])])
    assert validate_edit(_plan(), edited, user_edited=False) == []


def test_confirmed_vision_only_plan_can_activate():
    p = _plan(medicines=[_med(sourceBlockIds=[], source="vision_only", needsConfirmation=False)])
    assert validate_plan(p) == []
    assert can_activate(p) == []


# --- final review: R25 ---

def _stringify(value):
    if isinstance(value, dict):
        return {k: _stringify(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_stringify(v) for v in value]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return value


# --- fix pass 2: R28 ferrous salt change is a real dose change (finding 3) ---

def test_ferrous_salt_change_without_user_edited_is_rejected():
    original = _plan(medicines=[_med(molecules=[Molecule(name="Ferrous Sulphate", strengthMg=200)])])
    edited = _plan(medicines=[_med(molecules=[Molecule(name="Ferrous Ascorbate", strengthMg=200)])])
    assert validate_edit(original, edited, user_edited=False) != []
    assert validate_edit(original, edited, user_edited=True) == []


def test_dynamodb_round_trip_with_string_numbers_and_unknown_keys():
    original = _plan(medicines=[
        _med(durationDays=30, crop={"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.05}),
        _med(lineId="m2", molecules=[Molecule(name="Vitamin D3", strengthMg=60000, unit="iu")],
             sourceBlockIds=["b2"]),
    ])
    d = _stringify(original.to_dict())
    d["medicines"][0]["lineId"] = 1
    original.medicines[0].lineId = "1"
    d["medicines"][0]["futureField"] = "x"
    d["medicines"][0]["molecules"][0]["atcCode"] = "B01AC06"
    d["redFlags"]["lang"] = "kn"
    back = Plan.from_dict(d)
    assert back.medicines[0].lineId == "1"
    assert back.medicines[0].confidence == 0.95
    assert back.medicines[0].durationDays == 30
    assert back.medicines[0].molecules[0].strengthMg == 75.0
    assert back.medicines[0].crop == {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.05}
    assert validate_plan(back) == []
    assert validate_edit(original, back, False) == []
