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


def test_vision_only_medicine_may_have_no_blocks_but_must_confirm():
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
