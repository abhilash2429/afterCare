from api.drugs import normalise_molecule
from api.models import SLOTS

GENERIC_RED_FLAG_TEXT = (
    "Call your doctor or 108 immediately for: chest pain, breathlessness, heavy "
    "bleeding, fever above 101°F, fainting or confusion. This is general advice "
    "— it was not found in your document."
)

_CONFIDENCE_FLOOR = 0.85


def validate_plan(plan):
    """Spec section 7. Returns a list of human-readable errors; empty means valid."""
    errors = []
    rf = plan.redFlags
    if rf is not None:
        if rf.source not in ("document", "generic"):
            errors.append("redFlags.source must be 'document' or 'generic'")
        if rf.source == "document" and not rf.sourceBlockIds:
            errors.append("redFlags.sourceBlockIds must be non-empty when source is 'document'")
        if rf.source == "generic" and rf.text != GENERIC_RED_FLAG_TEXT:
            errors.append("redFlags.text must be the fixed generic constant")

    line_ids = [m.lineId for m in plan.medicines]
    dupes = sorted({x for x in line_ids if line_ids.count(x) > 1})
    if dupes:
        errors.append("duplicate lineId(s): %s" % ", ".join(dupes))

    for m in plan.medicines:
        has_values = bool(m.molecules) or m.frequency is not None or m.durationDays is not None
        if has_values and not m.sourceBlockIds and m.source not in ("vision_only", "user"):
            errors.append("%s: sourceBlockIds required for extracted values" % m.lineId)
        if m.prn and m.slots:
            errors.append("%s: prn medicines must not be scheduled (slots must be empty)" % m.lineId)
        if m.frequency is None and m.slots:
            errors.append("%s: slots present but frequency is null - never inferred" % m.lineId)
        if not m.prn and m.frequency is None and not m.needsConfirmation:
            errors.append("%s: frequency is null - needsConfirmation must be true" % m.lineId)
        for s in m.slots:
            if s not in SLOTS:
                errors.append("%s: unknown slot '%s'" % (m.lineId, s))
        if m.confidence is None:
            errors.append("%s: confidence is required" % m.lineId)
        elif m.confidence < _CONFIDENCE_FLOOR and not m.needsConfirmation:
            errors.append("%s: confidence below floor must set needsConfirmation" % m.lineId)
    return errors


def _dose_signature(plan):
    out = {}
    for m in plan.medicines:
        molecules = [(normalise_molecule(x.name), x.strengthMg, (x.unit or "").strip().lower())
                     for x in m.molecules]
        out[m.lineId] = (
            tuple(sorted(molecules, key=repr)),
            (m.frequency or "").lower(),
            tuple(sorted(m.slots)),
            bool(m.prn),
            m.durationDays,
        )
    return out


def _source_signature(plan):
    return {m.lineId: (m.source, tuple(sorted(m.sourceBlockIds))) for m in plan.medicines}


def validate_edit(original, edited, user_edited):
    """A dose or its provenance may only change with an explicit user edit.

    Duplicate lineIds are rejected regardless of user_edited (validate_plan
    always checks that). Without user_edited, the set of lineIds must be
    unchanged - no line may be added, removed, or renamed - and for a line in
    both plans none of molecules (normalised name, strength, unit), frequency,
    slots, prn, durationDays, source or sourceBlockIds may change.
    """
    errors = validate_plan(edited)
    if user_edited:
        orig_ids = {m.lineId for m in original.medicines}
        for m in edited.medicines:
            if m.lineId not in orig_ids and not (m.source == "user" and not m.sourceBlockIds):
                errors.append(
                    "%s: new lines must have source 'user' with empty sourceBlockIds"
                    % m.lineId)
        return errors

    orig_ids = {m.lineId for m in original.medicines}
    edited_ids = {m.lineId for m in edited.medicines}
    if orig_ids != edited_ids:
        errors.append("medicine lines added, removed, or renamed without userEdited=true")

    before, after = _dose_signature(original), _dose_signature(edited)
    for line_id, sig in after.items():
        if line_id in before and before[line_id] != sig:
            errors.append("%s: dose or frequency changed without userEdited=true" % line_id)
    before, after = _source_signature(original), _source_signature(edited)
    for line_id, sig in after.items():
        if line_id in before and before[line_id] != sig:
            errors.append("%s: source or sourceBlockIds changed without userEdited=true" % line_id)
    return errors


def can_activate(plan):
    errors = validate_plan(plan)
    if plan.redFlags is None:
        errors.append("redFlags required before activation")
    pending = [m.lineId for m in plan.medicines if m.needsConfirmation]
    if pending:
        errors.append("confirm these before activating: %s" % ", ".join(pending))
    if not plan.medicines:
        errors.append("plan has no medicines")
    return errors
