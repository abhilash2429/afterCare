import difflib
import re

from api.models import Molecule

_FORMS = r"\b(tab|tabs|tablet|cap|caps|capsule|syp|syrup|inj|injection|oint|drops|susp)\b"
_LEADING_PREFIX = r"^(t|c)\b\s*"
_MATCH_FLOOR = 0.88

_EACH_CLAUSE = r"^\s*each\b.*?\bcontains?\b\s*:?"
_EQ_TO = r"\b(?:eq\b\.?|equivalent)\s*to\b"
_THOUSANDS = r"(?<=\d),(?=(?:\d{2},)*\d{3}(?!\d))"  # 60,000 and Indian 6,00,000
_STRENGTH = r"(\d+(?:\.\d+)?)\s*(mcg|mg|g|ml|iu|i\.?u\.?)(?![a-zA-Z])"
_PER_VOLUME = r"(?:\s*/\s*\d*(?:\.\d+)?\s*(?:ml|mg|g)\b)?"
# Undotted (ip, bp, usp) and dotted (i.p., b.p., u.s.p.) pharmacopoeia tags. \b fails
# after a trailing period, so this uses lookaround instead.
_PHARMACOPOEIA = r"(?<![a-z])(?:i\.?p\.?|b\.?p\.?|u\.?s\.?p\.?)(?![a-z])"
_RELEASE_FORMS = (
    r"\b(?:tablets?|tabs?|capsules?|caps?|film[\s-]*coated|sr|er|xr|cr|mr|dt|"
    r"gastro[\s-]*resistant|enteric[\s-]*coated|"
    r"(?:prolonged|extended|modified|sustained|controlled)[\s-]*release|"
    r"oral[\s-]+suspension|suspension|syrup|syp|injection|inj|drops)\b"
)
_SALT_SUFFIX = r"\s+(?:hydrochloride|hcl|sodium|potassium)$"

# Only spellings of the same active drug. Every entry here merges two names into one
# match, so keep it tiny: a wrong entry would green-light a different medicine.
# Ferrous salts (ascorbate/fumarate/sulphate/sulfate) are deliberately NOT merged:
# they are different compounds a doctor can prescribe by design (R28).
MOLECULE_SYNONYMS = {
    "levothyroxine": "thyroxine",
    "alendronate": "alendronic acid",
    "amoxicillin": "amoxycillin",
    "acetaminophen": "paracetamol",
    "elemental iron": "iron",
    "potassium clavulanate": "clavulanic acid",
    "clavulanate": "clavulanic acid",
    "acetylsalicylic acid": "aspirin",
    "albuterol": "salbutamol",
    "glyceryl trinitrate": "nitroglycerin",
}


def normalise_brand(text):
    if not text:
        return ""
    t = str(text).lower()
    t = re.sub(r"\(.*?\)", " ", t)
    t = re.sub(r"[.\-/,]", " ", t)
    t = re.sub(_LEADING_PREFIX, "", t.strip())
    t = re.sub(_FORMS, " ", t)
    t = re.sub(r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml|iu)?\b", " ", t)
    t = re.sub(r"\bstrip of\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def bucket_key(normalised):
    return (normalised or "")[:4]


def normalise_molecule(name):
    """'Pantoprazole Sodium IP eq. to Pantoprazole' -> 'pantoprazole'. Name only, no strength."""
    t = re.sub(_EACH_CLAUSE, " ", str(name or "").lower())
    t = re.split(_EQ_TO, t)[-1]
    t = re.sub(_PHARMACOPOEIA, " ", t)
    t = re.sub(_RELEASE_FORMS, " ", t)
    t = re.sub(r"\s+", " ", t).strip(" .,:;")
    while True:
        stripped = re.sub(_SALT_SUFFIX, "", t)
        if stripped == t or not stripped:
            break
        t = stripped
    return MOLECULE_SYNONYMS.get(t, t)


def parse_composition(text):
    """'Amoxycillin (500mg) + Clavulanic Acid (125mg)' -> two Molecules (strength in mg)."""
    if not text:
        return []
    text = re.sub(_THOUSANDS, "", re.sub(_EACH_CLAUSE, " ", str(text), flags=re.I))
    out = []
    for part in re.split(r"\s*\+\s*", text):
        part = re.split(_EQ_TO, part, flags=re.I)[-1].strip()
        if not part:
            continue
        m = re.search(_STRENGTH, part, re.I)
        strength = None
        unit = "mg"
        if m:
            value, raw_unit = float(m.group(1)), m.group(2).lower().replace(".", "")
            if raw_unit in ("iu", "ml"):
                strength, unit = value, raw_unit
            else:
                strength = {"mcg": value / 1000.0, "g": value * 1000.0}.get(raw_unit, value)
        name = re.sub(r"\(.*?\)", " ", part)
        name = normalise_molecule(re.sub(_STRENGTH + _PER_VOLUME, " ", name, flags=re.I))
        if name:
            out.append(Molecule(name=name, strengthMg=strength, unit=unit))
    return out


def best_brand_match(query, candidates):
    """Exact first, then difflib. Returns (name, score) or (None, 0.0) below the floor."""
    q = normalise_brand(query)
    if not q or not candidates:
        return None, 0.0
    if q in candidates:
        return q, 1.0
    best, best_score = None, 0.0
    for c in candidates:
        score = difflib.SequenceMatcher(None, q, c).ratio()
        if score > best_score:
            best, best_score = c, score
    if best_score < _MATCH_FLOOR:
        return None, best_score
    return best, best_score


def same_drug(a, b):
    """Same normalised molecule in the same unit, strength ignored."""
    return (normalise_molecule(a.name) == normalise_molecule(b.name)
            and (a.unit or "").strip().lower() == (b.unit or "").strip().lower())


def molecules_equal(a, b):
    """Same drug and a known, equal strength. An unread strength is never equal."""
    if not same_drug(a, b) or a.strengthMg is None or b.strengthMg is None:
        return False
    return abs(float(a.strengthMg) - float(b.strengthMg)) < 0.001
