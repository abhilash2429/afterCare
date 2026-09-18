import io

import pytest

from api import extract
from api.models import Molecule
from api.validate import GENERIC_RED_FLAG_TEXT, validate_plan


def _box(left, top, width=0.1, height=0.02):
    return {"Left": left, "Top": top, "Width": width, "Height": height}


WORDS = [{"id": "w%d" % i, "text": "word%d" % i, "box": _box(0.1, 0.1 + i * 0.03)}
         for i in range(1, 26)]
WORDS[0]["text"], WORDS[1]["text"] = "Aspirin", "75"


def _page(*texts):
    words = [dict(w) for w in WORDS]
    for i, t in enumerate(texts):
        words[i]["text"] = t
    return words, ["w%d" % (i + 1) for i in range(len(texts))]


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


def _run(monkeypatch, raw, words=WORDS, key="circles/c1/doc.png", brands=None):
    seen = {}
    monkeypatch.setattr(extract, "lookup_brand",
                        lambda brand: list((brands or {}).get(brand, [])))

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
            {"name": "Odd", "strengthMg": "n/a", "unit": None},
            {"name": "Calcium Carbonate", "strengthMg": 1, "unit": "g"}]
    words, ids = _page("Acetylsalicylic", "Acid", "IP", "75mg", "Vitamin", "D3", "60,000",
                       "IU", "Levothyroxine", "25", "mcg", "Mystery", "Odd",
                       "(Calcium", "Carbonate", "1", "g)")
    mols[2]["strengthMg"] = 25
    plan, _ = _run(monkeypatch, {"medicines": [_med(molecules=mols, sourceBlockIds=ids)]},
                   words=words)
    got = [(x.name, x.strengthMg, x.unit) for x in plan.medicines[0].molecules]
    assert got == [("aspirin", 75.0, "mg"), ("vitamin d3", 60000.0, "iu"),
                   ("thyroxine", 0.025, "mg"), ("mystery", None, "mg"),
                   ("odd", None, "mg"), ("calcium carbonate", 1000.0, "mg")]
    assert plan.medicines[0].needsConfirmation is False


def test_printed_multi_word_generic_is_kept_as_is(monkeypatch):
    words, ids = _page("T.", "Sorbitrate", "(Isosorbide", "Dinitrate", "5", "mg)", "SOS")
    mols = [{"name": "Isosorbide dinitrate", "strengthMg": 5, "unit": "mg"}]
    plan, _ = _run(monkeypatch, {"medicines": [_med(
        brand="Sorbitrate", molecules=mols, frequency="SOS", sourceBlockIds=ids)]},
        words=words, brands={"Sorbitrate": [Molecule("nitroglycerin", 2.6)]})
    m = plan.medicines[0]
    assert [(x.name, x.strengthMg) for x in m.molecules] == [("isosorbide dinitrate", 5.0)]
    assert m.needsConfirmation is False


def test_generic_split_across_the_line_is_not_a_phrase_match(monkeypatch):
    words, ids = _page("Isosorbide", "5", "mg", "Dinitrate")
    mols = [{"name": "Isosorbide dinitrate", "strengthMg": 5, "unit": "mg"}]
    plan, _ = _run(monkeypatch, {"medicines": [_med(
        brand="Sorbitrate", molecules=mols, sourceBlockIds=ids)]}, words=words)
    assert (plan.medicines[0].molecules, plan.medicines[0].needsConfirmation) == ([], True)


def test_brand_only_line_takes_the_generic_from_the_dataset(monkeypatch):
    words, ids = _page("Syp.", "Levolin", "1", "mg/5", "ml", "2.5", "ml", "TDS")
    mols = [{"name": "Salbutamol", "strengthMg": 1, "unit": "mg"}]
    plan, _ = _run(monkeypatch, {"medicines": [_med(
        brand="Levolin", molecules=mols, frequency="TDS", sourceBlockIds=ids)]},
        words=words, brands={"Levolin": [Molecule("levosalbutamol", 1.0)]})
    m = plan.medicines[0]
    assert [(x.name, x.strengthMg, x.unit) for x in m.molecules] == \
        [("levosalbutamol", 1.0, "mg")]
    assert m.needsConfirmation is True


def test_brand_only_line_never_copies_the_dataset_strength(monkeypatch):
    words, ids = _page("T.", "Niftran", "1-0-1")
    mols = [{"name": "Nifedipine", "strengthMg": 100, "unit": "mg"}]
    plan, _ = _run(monkeypatch, {"medicines": [_med(
        brand="Niftran", molecules=mols, frequency="1-0-1", sourceBlockIds=ids)]},
        words=words, brands={"Niftran": [Molecule("nitrofurantoin", 100.0)]})
    m = plan.medicines[0]
    assert [(x.name, x.strengthMg) for x in m.molecules] == [("nitrofurantoin", None)]
    assert m.needsConfirmation is True


def test_brand_only_combination_pairs_printed_strengths_by_value(monkeypatch):
    words, ids = _page("Syp.", "Augmentin", "Duo", "(400", "mg", "+", "57", "mg", "BD")
    mols = [{"name": "Clavulanic acid", "strengthMg": 57, "unit": "mg"},
            {"name": "Amoxicillin", "strengthMg": 400, "unit": "mg"}]
    plan, _ = _run(monkeypatch, {"medicines": [_med(
        brand="Augmentin Duo", molecules=mols, frequency="BD", sourceBlockIds=ids)]},
        words=words, brands={"Augmentin Duo": [Molecule("amoxycillin", 400.0),
                                               Molecule("clavulanic acid", 57.0)]})
    m = plan.medicines[0]
    assert [(x.name, x.strengthMg) for x in m.molecules] == \
        [("amoxycillin", 400.0), ("clavulanic acid", 57.0)]
    assert m.needsConfirmation is True


def test_brand_lookup_miss_leaves_no_molecules(monkeypatch):
    words, ids = _page("T.", "Unknownix", "10", "mg", "OD")
    mols = [{"name": "Madeupzole", "strengthMg": 10, "unit": "mg"}]
    plan, _ = _run(monkeypatch, {"medicines": [_med(
        brand="Unknownix", molecules=mols, frequency="OD", sourceBlockIds=ids)]}, words=words)
    m = plan.medicines[0]
    assert (m.molecules, m.needsConfirmation) == ([], True)


def test_missing_frequency_needs_confirmation(monkeypatch):
    plan, _ = _run(monkeypatch, {"medicines": [_med(frequency=None)]})
    m = plan.medicines[0]
    assert (m.slots, m.needsConfirmation) == ([], True)
    assert validate_plan(plan) == []


def test_strength_not_printed_in_the_cited_words_needs_confirmation(monkeypatch):
    words, ids = _page("Amlodipine", "OD")
    plan, _ = _run(monkeypatch, {"medicines": [_med(
        molecules=[{"name": "Amlodipine", "strengthMg": 5, "unit": "mg"}],
        sourceBlockIds=ids)]}, words=words)
    assert plan.medicines[0].needsConfirmation is True


def test_strength_printed_in_the_cited_words_is_accepted(monkeypatch):
    words, ids = _page("Aspirin", "75mg")
    plan, _ = _run(monkeypatch, {"medicines": [_med(sourceBlockIds=ids)]}, words=words)
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
