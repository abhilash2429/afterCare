from dataclasses import dataclass, field
from typing import List, Optional

from api.drugs import molecules_equal, normalise_brand, normalise_molecule, same_drug
from api.models import Molecule

MESSAGES = {
    "exact_match": "This matches your prescription.",
    "strength_mismatch": "Same medicine, different strength. Check with your chemist.",
    "strength_unreadable": "We could not read the strength. Check with your chemist.",
    "combination_extra": "This strip has extra medicines in it. Check with your chemist.",
    "brand_unreadable": "We could not read the brand, but the medicine matches. Check with your chemist.",
    "unreadable_strip": "We could not read this strip. Check with your chemist.",
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
    return {normalise_molecule(m.name) for m in molecules}


def _covers(outer, inner):
    return all(any(molecules_equal(m, o) for o in outer) for m in inner)


def _same_set(a, b):
    return _covers(a, b) and _covers(b, a)


def _exact(med, strip):
    return bool(med.molecules) and _same_set(med.molecules, strip.molecules)


def _contains_more(med, strip):
    return (bool(med.molecules)
            and _covers(strip.molecules, med.molecules)
            and not _covers(med.molecules, strip.molecules))


def _strength_unreadable(med, strip):
    """Every prescribed drug is on the strip in the same unit, none at a known
    different strength, and at least one strength is unread on either side."""
    unread = False
    for m in med.molecules:
        same = [s for s in strip.molecules if same_drug(m, s)]
        if not same:
            return False
        if any(molecules_equal(m, s) for s in same):
            continue
        if m.strengthMg is not None and all(s.strengthMg is not None for s in same):
            return False
        unread = True
    return unread


def _near_item(med, strip):
    reason = "strength_unreadable" if _strength_unreadable(med, strip) else "strength_mismatch"
    return _item("check", reason, med.lineId, strip)


def _exact_item(line_id, strip):
    if strip.brandText:
        return _item("matched", "exact_match", line_id, strip)
    return _item("check", "brand_unreadable", line_id, strip)


def _same_pack(a, b):
    """Another pack of the same product: same molecules, and the same brand
    unless either brand is unreadable."""
    ba, bb = normalise_brand(a.brandText), normalise_brand(b.brandText)
    return (not ba or not bb or ba == bb) and _same_set(a.molecules, b.molecules)


def check_box(medicines, strips):
    """Compare prescribed lines to photographed strips.

    Every prescribed line gets exactly one primary item, in plan order. After
    those, every strip no line consumed gets one item: an extra pack of a line
    (carrying that line's id), a second product duplicating a satisfied line
    (duplicate_molecule), an unreadable strip, or not_prescribed (id None).
    So a line can have more than one item, but only its first is the primary
    verdict.

    Order: duplicate flags, exact matches for non-duplicate lines, a PRN line
    sharing the strip of a regular line of the same drug, then the duplicate
    lines take their own exact strips, then combination, name-only and missing
    for whatever is still unresolved. Exact runs over all lines before any
    fallback so a looser line cannot steal another line's strip. A strip with
    no molecules is never consumed by a line.
    """
    primary = {}
    satisfied = {}
    used = set()
    prescribed = [m for med in medicines for m in med.molecules]

    # A PRN line and a regular line of the same drug are the doctor's own plan
    # (paracetamol TDS + SOS), so only lines with the same prn flag duplicate.
    duplicates = set()
    for i, med in enumerate(medicines):
        names = _names(med.molecules)
        if any(names & _names(e.molecules) and e.prn == med.prn for e in medicines[:i]):
            duplicates.add(med.lineId)
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
            satisfied[med.lineId] = strip

    for med in normal:
        if med.lineId in primary:
            continue
        owner = next((o for o in normal if o.lineId in satisfied and o.prn != med.prn
                      and _exact(med, satisfied[o.lineId])), None)
        if owner:
            strip = satisfied[owner.lineId]
            primary[med.lineId] = _exact_item(med.lineId, strip)
            satisfied[med.lineId] = strip

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
                # A combo strip's extra molecule (not this line's own) may already
                # have its own exact-matched strip on another line - that's double
                # dosing, not a combination to check with the chemist.
                own_names = _names(med.molecules)
                extras = [m for m in strip.molecules if normalise_molecule(m.name) not in own_names]
                dup = False
                for other_id, other_strip in satisfied.items():
                    if other_strip is strip:
                        continue
                    other_med = next(o for o in medicines if o.lineId == other_id)
                    if any(molecules_equal(om, em) for om in other_med.molecules for em in extras):
                        dup = True
                        break
                if dup:
                    primary[med.lineId] = _item("do_not_take", "duplicate_molecule", med.lineId, strip)
                else:
                    if _covers(prescribed, strip.molecules):
                        reason = "combination_strip"
                    else:
                        reason = "combination_extra"
                    primary[med.lineId] = _item("check", reason, med.lineId, strip)
                    satisfied[med.lineId] = strip
                break

    for med in normal:
        if med.lineId in primary:
            continue
        strip = take(med, lambda m, s: _names(m.molecules) & _names(s.molecules))
        primary[med.lineId] = (_near_item(med, strip) if strip
                               else _item("do_not_take", "missing_from_box", med.lineId, None))

    items = [primary[med.lineId] for med in medicines]
    satisfied_lines = [med for med in medicines if med.lineId in satisfied]
    satisfied_molecules = [m for med in satisfied_lines for m in med.molecules]
    for i, strip in enumerate(strips):
        if i in used:
            continue
        if not strip.molecules:
            items.append(_item("check", "unreadable_strip", None, strip))
            continue
        pack = next((med for med in satisfied_lines
                     if _same_pack(satisfied[med.lineId], strip)), None)
        exact = next((med for med in medicines if _exact(med, strip)), None)
        similar = next((med for med in medicines
                        if _names(med.molecules) & _names(strip.molecules)), None)
        if pack:
            reason = primary[pack.lineId]["reason"]
            if reason in ("exact_match", "brand_unreadable"):
                items.append(_exact_item(pack.lineId, strip))
            else:
                items.append(_item("check", reason, pack.lineId, strip))
        elif exact:
            items.append(_item("do_not_take", "duplicate_molecule", exact.lineId, strip))
        elif len(strip.molecules) > 1 and _covers(satisfied_molecules, strip.molecules):
            owner = next(med for med in satisfied_lines
                         if _names(med.molecules) & _names(strip.molecules))
            items.append(_item("do_not_take", "duplicate_molecule", owner.lineId, strip))
        elif similar:
            items.append(_near_item(similar, strip))
        else:
            items.append(_item("do_not_take", "not_prescribed", None, strip))
    return items
