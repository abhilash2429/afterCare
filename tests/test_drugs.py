from api.models import Molecule
from api.drugs import (normalise_brand, bucket_key, parse_composition,
                       best_brand_match, molecules_equal)


def test_normalise_strips_form_strength_and_pack():
    assert normalise_brand("Tab. Ecosprin 75mg (strip of 14)") == "ecosprin"
    assert normalise_brand("T.Pan-40") == "pan"
    assert normalise_brand("CAP AMOXYCLAV 625 DUO") == "amoxyclav duo"


def test_normalise_keeps_standalone_c_that_is_not_a_prefix():
    assert normalise_brand("Vitamin C 500mg") == "vitamin c"


def test_normalise_strips_leading_capital_prefix():
    assert normalise_brand("C. Amoxyclav 625") == "amoxyclav"


def test_bucket_key_is_first_four_chars():
    assert bucket_key("ecosprin") == "ecos"
    assert bucket_key("pan") == "pan"


def test_parse_composition_single_and_combination():
    assert parse_composition("Aspirin (75mg)") == [Molecule("aspirin", 75)]
    got = parse_composition("Amoxycillin (500mg) + Clavulanic Acid (125mg)")
    assert got == [Molecule("amoxycillin", 500), Molecule("clavulanic acid", 125)]


def test_parse_composition_handles_mcg_and_missing_strength():
    assert parse_composition("Levothyroxine (25mcg)") == [Molecule("levothyroxine", 0.025)]
    assert parse_composition("Multivitamin") == [Molecule("multivitamin", None)]


def test_parse_composition_keeps_iu_as_its_own_unit():
    assert parse_composition("Vitamin D3 (60000IU)") == [Molecule("vitamin d3", 60000, "iu")]


def test_best_brand_match_prefers_exact_then_close():
    assert best_brand_match("ecosprin", ["ecosprin", "ecosprin av"])[0] == "ecosprin"
    name, score = best_brand_match("ecosprn", ["ecosprin", "zincovit"])
    assert name == "ecosprin" and score >= 0.88
    assert best_brand_match("qwertyzz", ["ecosprin"])[0] is None


def test_molecules_equal_ignores_case_and_matches_strength():
    assert molecules_equal(Molecule("Aspirin", 75), Molecule("aspirin", 75.0))
    assert not molecules_equal(Molecule("Aspirin", 75), Molecule("Aspirin", 150))


def test_molecules_equal_requires_matching_unit():
    assert molecules_equal(Molecule("vitamin d3", 60000, "iu"), Molecule("vitamin d3", 60000, "iu")) is True
    assert molecules_equal(Molecule("vitamin d3", 60000, "iu"), Molecule("vitamin d3", 60000, "mg")) is False
