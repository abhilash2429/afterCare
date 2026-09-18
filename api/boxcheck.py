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
        "stripMolecules": [{"name": m.name, "strengthMg": m.strengthMg}
                           for m in (strip.molecules if strip else [])],
    }


def check_box(medicines, strips):
    items = []
    used = set()

    for med in medicines:
        matched_index = None
        fallback = None
        for i, strip in enumerate(strips):
            if i in used:
                continue
            hits = [m for m in med.molecules
                    if any(molecules_equal(m, s) for s in strip.molecules)]
            if hits and len(hits) == len(med.molecules):
                if len(strip.molecules) > len(med.molecules):
                    fallback = fallback or (i, "combination_extra")
                elif not strip.brandText:
                    fallback = fallback or (i, "brand_unreadable")
                else:
                    matched_index = i
                    break
            elif any(m.name.lower() == s.name.lower() for m in med.molecules
                     for s in strip.molecules):
                fallback = fallback or (i, "strength_mismatch")

        if matched_index is not None:
            used.add(matched_index)
            items.append(_item("matched", "exact_match", med.lineId, strips[matched_index]))
        elif fallback is not None:
            i, reason = fallback
            used.add(i)
            items.append(_item("check", reason, med.lineId, strips[i]))
        else:
            items.append(_item("do_not_take", "missing_from_box", med.lineId, None))

    for i, strip in enumerate(strips):
        if i not in used:
            items.append(_item("do_not_take", "not_prescribed", None, strip))

    seen = {}
    for med in medicines:
        for mol in med.molecules:
            key = mol.name.strip().lower()
            if key in seen and seen[key] != med.lineId:
                items.append(_item("do_not_take", "duplicate_molecule", med.lineId, None))
            else:
                seen[key] = med.lineId
    return items
