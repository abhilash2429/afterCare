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
    assert parse_composition("Levothyroxine (25mcg)") == [Molecule("thyroxine", 0.025)]
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


# --- final review: R20 / R26 / R22 ---

from api.drugs import normalise_molecule


def test_normalise_molecule_strips_pharmacopoeia_form_and_salt():
    assert normalise_molecule("Aspirin IP") == "aspirin"
    assert normalise_molecule("Metformin HCl SR") == "metformin"
    assert normalise_molecule("Metformin Hydrochloride") == "metformin"
    assert normalise_molecule("Paracetamol Tablet") == "paracetamol"
    assert normalise_molecule("Losartan Potassium USP") == "losartan"
    assert normalise_molecule("Sodium") == "sodium"


def test_normalise_molecule_keeps_leading_salt_word():
    # suffix-only: sodium chloride and potassium chloride must never collapse together
    assert normalise_molecule("Potassium Chloride") == "potassium chloride"
    assert normalise_molecule("Sodium Chloride") == "sodium chloride"


def test_normalise_molecule_resolves_each_contains_and_eq_to():
    text = "Each film coated tablet contains: Pantoprazole Sodium IP eq. to Pantoprazole"
    assert normalise_molecule(text) == "pantoprazole"
    assert normalise_molecule("Ferrous Ascorbate equivalent to Elemental Iron") == "iron"


def test_normalise_molecule_synonyms():
    assert normalise_molecule("Amoxicillin") == "amoxycillin"
    assert normalise_molecule("Acetaminophen") == "paracetamol"
    assert normalise_molecule("Elemental Iron") == "iron"


def test_parse_composition_realistic_strip_text():
    assert parse_composition("Aspirin IP 75 mg") == [Molecule("aspirin", 75)]
    assert parse_composition("Metformin HCl 500 mg SR") == [Molecule("metformin", 500)]
    assert parse_composition("Paracetamol 500 mg Tablet") == [Molecule("paracetamol", 500)]
    assert parse_composition(
        "Each film coated tablet contains: Pantoprazole Sodium IP eq. to Pantoprazole 40 mg"
    ) == [Molecule("pantoprazole", 40)]


def test_parse_composition_eq_to_takes_the_equivalent_strength():
    assert parse_composition("Pantoprazole Sodium IP 45.1 mg eq. to Pantoprazole 40 mg") == [
        Molecule("pantoprazole", 40)]


def test_parse_composition_each_5ml_clause_is_not_the_strength():
    assert parse_composition("Each 5 ml contains: Amoxycillin 125 mg") == [Molecule("amoxycillin", 125)]


def test_parse_composition_thousands_separator():
    assert parse_composition("Vitamin D3 60,000 IU") == [Molecule("vitamin d3", 60000, "iu")]
    assert parse_composition("Cholecalciferol 6,00,000 IU") == [Molecule("cholecalciferol", 600000, "iu")]


def test_parse_composition_per_volume_denominator_not_in_name():
    got = parse_composition("Amoxycillin 125mg/5ml")
    assert got == [Molecule("amoxycillin", 125)]
    assert "/" not in got[0].name


def test_molecules_equal_uses_normalised_names():
    assert molecules_equal(Molecule("Amoxicillin", 500), Molecule("amoxycillin", 500))
    assert molecules_equal(Molecule("Pantoprazole Sodium IP", 40), Molecule("pantoprazole", 40))


def test_molecules_equal_requires_known_strength():
    assert not molecules_equal(Molecule("multivitamin", None), Molecule("multivitamin", None))
    assert not molecules_equal(Molecule("aspirin", None), Molecule("aspirin", 75))


# --- fix pass 2: R27 normaliser coverage (finding 2) ---

def test_normalise_molecule_handles_dotted_pharmacopoeia():
    assert normalise_molecule("Aspirin I.P.") == "aspirin"
    assert normalise_molecule("Metformin B.P.") == "metformin"
    assert normalise_molecule("Losartan U.S.P.") == "losartan"


def test_normalise_molecule_strips_release_and_form_words():
    assert normalise_molecule("Aspirin Gastro-resistant") == "aspirin"
    assert normalise_molecule("Aspirin Gastro resistant") == "aspirin"
    assert normalise_molecule("Amoxycillin Enteric Coated") == "amoxycillin"
    assert normalise_molecule("Metformin Prolonged-release") == "metformin"
    assert normalise_molecule("Metformin Prolonged release") == "metformin"
    assert normalise_molecule("Metformin Extended-release") == "metformin"
    assert normalise_molecule("Metformin Modified release") == "metformin"
    assert normalise_molecule("Metformin Sustained-release") == "metformin"
    assert normalise_molecule("Metformin Controlled-release") == "metformin"
    assert normalise_molecule("Paracetamol Tab") == "paracetamol"
    assert normalise_molecule("Paracetamol Tabs") == "paracetamol"
    assert normalise_molecule("Amoxycillin Cap") == "amoxycillin"
    assert normalise_molecule("Amoxycillin Caps") == "amoxycillin"
    assert normalise_molecule("Paracetamol Syrup") == "paracetamol"
    assert normalise_molecule("Paracetamol Syp") == "paracetamol"
    assert normalise_molecule("Paracetamol Suspension") == "paracetamol"
    assert normalise_molecule("Paracetamol Oral Suspension") == "paracetamol"
    assert normalise_molecule("Ceftriaxone Injection") == "ceftriaxone"
    assert normalise_molecule("Ceftriaxone Inj") == "ceftriaxone"
    assert normalise_molecule("Atropine Drops") == "atropine"


def test_parse_composition_dotted_pharmacopoeia_and_release_words():
    assert parse_composition("Aspirin Gastro-resistant Tablets I.P. 75 mg") == [
        Molecule("aspirin", 75.0, "mg")]
    assert parse_composition("Metformin Hydrochloride Prolonged-release Tablets IP 500 mg") == [
        Molecule("metformin", 500.0, "mg")]
    assert parse_composition("Paracetamol Tab IP 650 mg") == [Molecule("paracetamol", 650.0, "mg")]


def test_parse_composition_dotted_iu_unit():
    assert parse_composition("Vitamin D3 60,000 I.U.") == [Molecule("vitamin d3", 60000.0, "iu")]


def test_parse_composition_clavulanate_potassium_synonym():
    got = parse_composition("Amoxycillin 500mg + Potassium Clavulanate 125mg")
    assert got == [Molecule("amoxycillin", 500.0, "mg"), Molecule("clavulanic acid", 125.0, "mg")]


def test_normalise_molecule_sodium_and_potassium_chloride_stay_distinct():
    assert normalise_molecule("sodium chloride") != normalise_molecule("potassium chloride")


# --- fix pass 2: R28 ferrous salts are no longer merged as synonyms (finding 3) ---

def test_normalise_molecule_no_longer_merges_ferrous_salts():
    assert normalise_molecule("Ferrous Sulphate") != "iron"
    assert normalise_molecule("Ferrous Ascorbate") != "iron"
    assert normalise_molecule("Ferrous Fumarate") != "iron"
    assert normalise_molecule("Ferrous Sulfate") != "iron"


def test_same_compound_spellings_map_to_the_dataset_name():
    assert normalise_molecule("Acetylsalicylic Acid") == "aspirin"
    assert normalise_molecule("Albuterol") == "salbutamol"
    assert normalise_molecule("Glyceryl Trinitrate") == "nitroglycerin"


def test_of_is_part_of_a_brand_not_noise():
    assert normalise_brand("Of Pan 400mg Tablet") == "of pan"
    assert normalise_brand("PAN 40 Tablet") == "pan"


def test_same_compound_spellings_match_dataset_names():
    from api.drugs import normalise_molecule
    assert normalise_molecule("Levothyroxine") == normalise_molecule("Thyroxine Sodium")
    assert normalise_molecule("Alendronate Sodium") == normalise_molecule("Alendronic Acid")
