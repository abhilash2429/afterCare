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

    for m in plan.medicines:
        has_values = bool(m.molecules) or m.frequency is not None or m.durationDays is not None
        if has_values and not m.sourceBlockIds and m.source != "vision_only":
            errors.append("%s: sourceBlockIds required for extracted values" % m.lineId)
        if m.source == "vision_only" and not m.needsConfirmation:
            errors.append("%s: vision_only medicines must set needsConfirmation" % m.lineId)
        if m.prn and m.slots:
            errors.append("%s: prn medicines must not be scheduled (slots must be empty)" % m.lineId)
        if m.frequency is None and m.slots:
            errors.append("%s: slots present but frequency is null - never inferred" % m.lineId)
        if m.confidence < _CONFIDENCE_FLOOR and not m.needsConfirmation:
            errors.append("%s: confidence below floor must set needsConfirmation" % m.lineId)
    return errors


def _dose_signature(plan):
    out = {}
    for m in plan.medicines:
        out[m.lineId] = (
            tuple(sorted((x.name.lower(), x.strengthMg) for x in m.molecules)),
            (m.frequency or "").lower(),
        )
    return out


def validate_edit(original, edited, user_edited):
    """A strength or frequency may only change with an explicit user edit."""
    errors = validate_plan(edited)
    if user_edited:
        return errors
    before, after = _dose_signature(original), _dose_signature(edited)
    for line_id, sig in after.items():
        if line_id in before and before[line_id] != sig:
            errors.append("%s: dose or frequency changed without userEdited=true" % line_id)
    return errors


def can_activate(plan):
    errors = validate_plan(plan)
    pending = [m.lineId for m in plan.medicines if m.needsConfirmation]
    if pending:
        errors.append("confirm these before activating: %s" % ", ".join(pending))
    if not plan.medicines:
        errors.append("plan has no medicines")
    return errors
