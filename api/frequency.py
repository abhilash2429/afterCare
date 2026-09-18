import re

_WORD = {
    "od": ["morning"], "qd": ["morning"], "daily": ["morning"], "once daily": ["morning"],
    "bd": ["morning", "night"], "bid": ["morning", "night"], "twice daily": ["morning", "night"],
    "tds": ["morning", "noon", "night"], "tid": ["morning", "noon", "night"],
    "qid": ["morning", "noon", "night", "bedtime"], "qds": ["morning", "noon", "night", "bedtime"],
    "hs": ["bedtime"], "nocte": ["bedtime"], "at bedtime": ["bedtime"],
}
_PRN = ("sos", "prn", "as needed", "if needed", "when required")
# "3.5 ml BD", "2 puffs BD": the dose amount written in front of the frequency.
_DOSE_PREFIX = r"^\d+(?:\.\d+)?\s*(?:ml|tabs?|tablets?|caps?|capsules?|puffs?|drops?)\s+"
_POSITIONAL_3 =["morning", "noon", "night"]
_POSITIONAL_4 = ["morning", "noon", "night", "bedtime"]


def parse_frequency(text):
    """Return (slots, is_prn). Unknown input returns ([], False) - never guessed."""
    if not text:
        return [], False
    t = re.sub(_DOSE_PREFIX, "", str(text).strip().lower())
    t = re.sub(r"[.\s]+", " ", t).strip()
    if any(p in t for p in _PRN):
        return [], True
    squashed = t.replace(" ", "")
    if squashed in _WORD:
        return list(_WORD[squashed]), False
    if t in _WORD:
        return list(_WORD[t]), False
    m = re.fullmatch(r"(\d)\s*-\s*(\d)\s*-\s*(\d)(?:\s*-\s*(\d))?", t)
    if m:
        digits = [g for g in m.groups() if g is not None]
        names = _POSITIONAL_4 if len(digits) == 4 else _POSITIONAL_3
        return [names[i] for i, d in enumerate(digits) if d != "0"], False
    return [], False
