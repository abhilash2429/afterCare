import difflib
import re

from api.models import Molecule

_FORMS = r"\b(tab|tabs|tablet|cap|caps|capsule|syp|syrup|inj|injection|oint|drops|susp|t|c)\b"
_MATCH_FLOOR = 0.88


def normalise_brand(text):
    if not text:
        return ""
    t = str(text).lower()
    t = re.sub(r"\(.*?\)", " ", t)
    t = re.sub(r"[.\-/,]", " ", t)
    t = re.sub(_FORMS, " ", t)
    t = re.sub(r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml|iu)?\b", " ", t)
    t = re.sub(r"\bstrip of\b|\bof\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def bucket_key(normalised):
    return (normalised or "")[:4]


def parse_composition(text):
    """'Amoxycillin (500mg) + Clavulanic Acid (125mg)' -> two Molecules (strength in mg)."""
    if not text:
        return []
    out = []
    for part in re.split(r"\s*\+\s*", str(text)):
        part = part.strip()
        if not part:
            continue
        m = re.search(r"\(?\s*(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|iu)\s*\)?", part, re.I)
        strength = None
        if m:
            value, unit = float(m.group(1)), m.group(2).lower()
            strength = {"mcg": value / 1000.0, "g": value * 1000.0}.get(unit, value)
        name = re.sub(r"\(.*?\)", " ", part)
        name = re.sub(r"\d+(\.\d+)?\s*(mg|mcg|g|ml|iu)", " ", name, flags=re.I)
        name = re.sub(r"\s+", " ", name).strip().lower()
        if name:
            out.append(Molecule(name=name, strengthMg=strength))
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


def molecules_equal(a, b):
    if a.name.strip().lower() != b.name.strip().lower():
        return False
    if a.strengthMg is None or b.strengthMg is None:
        return a.strengthMg == b.strengthMg
    return abs(float(a.strengthMg) - float(b.strengthMg)) < 0.001
