from dataclasses import dataclass, field
from typing import List, Optional

from api.drugs import molecules_equal
from api.models import Molecule

MESSAGES = {
    "exact_match": "This matches your prescription.",
    "strength_mismatch": "Same medicine, different strength. Check with your chemist.",
    "combination_extra": "This strip has extra medicines in it. Check with your chemist.",
    "brand_unreadable": "We could not read the brand, but the medicine matches. Check with your chemist.",
    "missing_from_box": "This medicine is not in the box. Do not skip it - ask your doctor.",
    "not_prescribed": "This is not on your prescription. Do not take it - ask your doctor.",
    "duplicate_molecule": "Two of your medicines contain the same drug. Do not take both - ask your doctor.",
    "combination_strip": "This strip combines more than one of your medicines in one tablet. Check with your chemist.",
}


@dataclass
class Strip:
    brandText: Optional[str]
    molecules: List[Molecule] = field(default_factory=list)


def _item(verdict, reason, line_id, strip):
    return {
        "verdict": verdict,
        "reason": reason,
        "message": MESSAGES[reason],
        "prescribedLineId": line_id,
        "stripBrandText": strip.brandText if strip else None,
        "stripMolecules": [{"name": m.name, "strengthMg": m.strengthMg, "unit": m.unit}
                           for m in (strip.molecules if strip else [])],
    }


def _names(molecules):
    return {m.name.strip().lower() for m in molecules}


def _covers(outer, inner):
    return all(any(molecules_equal(m, o) for o in outer) for m in inner)


def _exact(med, strip):
    return bool(med.molecules) and _covers(strip.molecules, med.molecules)         and _covers(med.molecules, strip.molecules)


def _contains_more(med, strip):
    return bool(med.molecules) and _covers(strip.molecules, med.molecules)         and not _covers(med.molecules, strip.molecules)


def _exact_item(line_id, strip):
    if strip.brandText:
        return _item("matched", "exact_match", line_id, strip)
    return _item("check", "brand_unreadable", line_id, strip)


def check_box(medicines, strips):
    """Compare prescribed lines to photographed strips.

    Every prescribed line gets exactly one primary item, in plan order. After
    those, every strip no line consumed gets one item: an extra pack of a line
    (carrying that line's id) or not_prescribed (id None). So a line can have
    more than one item, but only its first is the primary verdict.

    Order: duplicate flags, exact matches for non-duplicate lines, then the
    duplicate lines take their own exact strips, then combination, name-only
    and missing for whatever is still unresolved. Exact runs over all lines
    before any fallback so a looser line cannot steal another line's strip.
    """
    primary = {}
    used = set()
    prescribed = [m for med in medicines for m in med.molecules]

    seen, duplicates = set(), set()
    for med in medicines:
        names = _names(med.molecules)
        if names & seen:
            duplicates.add(med.lineId)
        seen |= names
    normal = [med for med in medicines if med.lineId not in duplicates]

    def take(med, match):
        for i, strip in enumerate(strips):
            if i not in used and match(med, strip):
                used.add(i)
                return strip
        return None

    for med in normal:
        strip = take(med, _exact)
        if strip:
            primary[med.lineId] = _exact_item(med.lineId, strip)

    for med in medicines:
        if med.lineId in duplicates:
            strip = take(med, _exact)
            primary[med.lineId] = _item("do_not_take", "duplicate_molecule", med.lineId, strip)

    combos = set()
    for med in normal:
        if med.lineId in primary:
            continue
        for i, strip in enumerate(strips):
            if (i not in used or i in combos) and _contains_more(med, strip):
                used.add(i)
                combos.add(i)
                reason = "combination_strip" if _covers(prescribed, strip.molecules)                     else "combination_extra"
                primary[med.lineId] = _item("check", reason, med.lineId, strip)
                break

    for med in normal:
        if med.lineId in primary:
            continue
        strip = take(med, lambda m, s: _names(m.molecules) & _names(s.molecules))
        primary[med.lineId] = (_item("check", "strength_mismatch", med.lineId, strip) if strip
                               else _item("do_not_take", "missing_from_box", med.lineId, None))

    items = [primary[med.lineId] for med in medicines]
    for i, strip in enumerate(strips):
        if i in used:
            continue
        exact = next((med for med in medicines if _exact(med, strip)), None)
        similar = next((med for med in medicines
                        if _names(med.molecules) & _names(strip.molecules)), None)
        if exact and exact.lineId in duplicates:
            items.append(_item("do_not_take", "duplicate_molecule", exact.lineId, strip))
        elif exact:
            items.append(_exact_item(exact.lineId, strip))
        elif similar:
            items.append(_item("check", "strength_mismatch", similar.lineId, strip))
        else:
            items.append(_item("do_not_take", "not_prescribed", None, strip))
    return items
