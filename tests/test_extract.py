import io

import pytest

from api import extract
from api.validate import GENERIC_RED_FLAG_TEXT, validate_plan


def _box(left, top, width=0.1, height=0.02):
    return {"Left": left, "Top": top, "Width": width, "Height": height}


WORDS = [{"id": "w%d" % i, "text": "word%d" % i, "box": _box(0.1, 0.1 + i * 0.03)}
         for i in range(1, 26)]
WORDS[0]["text"], WORDS[1]["text"] = "Ecosprin", "75"


def test_crop_for_is_the_padded_union_of_the_cited_words():
    words = [{"id": "a", "text": "", "box": _box(0.2, 0.3, 0.1, 0.05)},
             {"id": "b", "text": "", "box": _box(0.5, 0.4, 0.2, 0.05)}]
    crop = extract.crop_for(["a", "b"], words)
    assert crop == pytest.approx({"x": 0.19, "y": 0.29, "w": 0.52, "h": 0.17})


def test_crop_for_clamps_to_the_page():
    words = [{"id": "a", "text": "", "box": _box(0.0, 0.0, 1.0, 1.0)}]
    assert extract.crop_for(["a"], words) == {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}


def test_crop_for_unknown_ids_is_none():
    assert extract.crop_for(["zz"], WORDS) is None
    assert extract.crop_for([], WORDS) is None


class _Textract:
    def __init__(self, words):
        self.words = words

    def analyze_document(self, **kwargs):
        return {"Blocks": [{"BlockType": "WORD", "Id": w["id"], "Text": w["text"],
                            "Geometry": {"BoundingBox": w["box"]}} for w in self.words]}


class _S3:
    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(b"png-bytes")}


def _run(monkeypatch, raw, words=WORDS, key="circles/c1/doc.png"):
    seen = {}

    def fake_model(image, fmt, words_, model_id):
        seen.update(image=image, fmt=fmt)
        return raw

    monkeypatch.setattr(extract, "_textract", _Textract(words))
    monkeypatch.setattr(extract, "_s3", _S3())
    monkeypatch.setattr(extract, "_call_model", fake_model)
    return extract.extract_plan([key], "c1", model_id="m"), seen


def _med(**over):
    m = {"rawText": "T. Ecosprin 75 1-0-0", "brand": "Ecosprin",
         "molecules": [{"name": "Aspirin", "strengthMg": 75, "unit": "mg"}],
         "frequency": "1-0-0", "foodRelation": "after", "durationDays": 30,
         "confidence": 0.97, "sourceBlockIds": ["w1", "w2"]}
    m.update(over)
    return m


def test_clean_line_is_extracted_with_a_crop(monkeypatch):
    plan, seen = _run(monkeypatch, {"medicines": [_med()]})
    m = plan.medicines[0]
    assert (m.slots, m.needsConfirmation, m.source) == (["morning"], False, "textract")
    assert m.crop is not None
    assert seen == {"image": b"png-bytes", "fmt": "png"}
    assert validate_plan(plan) == []


def test_image_format_follows_the_key_extension(monkeypatch):
    _, seen = _run(monkeypatch, {"medicines": []}, key="circles/c1/doc.JPG")
    assert seen["fmt"] == "jpeg"


def test_invented_block_ids_are_dropped(monkeypatch):
    plan, _ = _run(monkeypatch, {"medicines": [_med(sourceBlockIds=["w1", "nope"])]})
    assert plan.medicines[0].sourceBlockIds == ["w1"]


def test_line_without_valid_block_ids_needs_confirmation(monkeypatch):
    plan, _ = _run(monkeypatch, {"medicines": [_med(sourceBlockIds=["nope"])]})
    m = plan.medicines[0]
    assert (m.sourceBlockIds, m.needsConfirmation, m.crop) == ([], True, None)


def test_molecules_are_normalised_and_units_carried(monkeypatch):
    mols = [{"name": "Acetylsalicylic Acid IP", "strengthMg": "75", "unit": "MG"},
            {"name": "Vitamin D3", "strengthMg": 60000, "unit": "IU"},
            {"name": "Levothyroxine", "strengthMg": 50, "unit": "mcg"},
            {"name": "Mystery", "strengthMg": None, "unit": "tabs"},
            {"name": "Odd", "strengthMg": "n/a", "unit": None}]
    plan, _ = _run(monkeypatch, {"medicines": [_med(molecules=mols)]})
    got = [(x.name, x.strengthMg, x.unit) for x in plan.medicines[0].molecules]
    assert got == [("aspirin", 75.0, "mg"), ("vitamin d3", 60000.0, "iu"),
                   ("levothyroxine", 0.05, "mg"), ("mystery", None, "mg"),
                   ("odd", None, "mg")]


def test_missing_frequency_needs_confirmation(monkeypatch):
    plan, _ = _run(monkeypatch, {"medicines": [_med(frequency=None)]})
    m = plan.medicines[0]
    assert (m.slots, m.needsConfirmation) == ([], True)
    assert validate_plan(plan) == []


def test_strength_not_printed_in_the_cited_words_needs_confirmation(monkeypatch):
    words = [dict(w) for w in WORDS]
    words[0]["text"], words[1]["text"] = "Amlodipine", "OD"
    plan, _ = _run(monkeypatch, {"medicines": [_med(
        molecules=[{"name": "Amlodipine", "strengthMg": 5, "unit": "mg"}])]}, words=words)
    assert plan.medicines[0].needsConfirmation is True


def test_strength_printed_in_the_cited_words_is_accepted(monkeypatch):
    words = [dict(w) for w in WORDS]
    words[0]["text"], words[1]["text"] = "Ecosprin", "75mg"
    plan, _ = _run(monkeypatch, {"medicines": [_med()]}, words=words)
    assert plan.medicines[0].needsConfirmation is False


def test_low_confidence_needs_confirmation(monkeypatch):
    plan, _ = _run(monkeypatch, {"medicines": [_med(confidence=0.5)]})
    assert plan.medicines[0].needsConfirmation is True


def test_few_words_is_vision_only_and_needs_confirmation(monkeypatch):
    plan, _ = _run(monkeypatch, {"medicines": [_med()]}, words=WORDS[:5])
    m = plan.medicines[0]
    assert (m.source, m.needsConfirmation) == ("vision_only", True)


def test_document_red_flags_keep_their_valid_ids(monkeypatch):
    rf = {"present": True, "text": "Report if chest pain", "sourceBlockIds": ["w3", "x"]}
    plan, _ = _run(monkeypatch, {"medicines": [], "redFlags": rf})
    assert (plan.redFlags.source, plan.redFlags.sourceBlockIds) == ("document", ["w3"])


def test_red_flags_without_valid_ids_fall_back_to_generic(monkeypatch):
    rf = {"present": True, "text": "Invented warning", "sourceBlockIds": ["nope"]}
    plan, _ = _run(monkeypatch, {"medicines": [], "redFlags": rf})
    assert (plan.redFlags.source, plan.redFlags.text) == ("generic", GENERIC_RED_FLAG_TEXT)
    assert plan.redFlags.sourceBlockIds == []
    assert validate_plan(plan) == []
