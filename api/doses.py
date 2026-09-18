from datetime import timedelta

from api.models import SLOTS, Dose

DEFAULT_DAYS = 7


def build_doses(plan, start_date, days=7):
    doses = []
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        by_slot = {}
        for med in plan.medicines:
            if med.prn or not med.slots:
                continue
            limit = med.durationDays if med.durationDays is not None else DEFAULT_DAYS
            if offset >= limit:
                continue
            for slot in med.slots:
                by_slot.setdefault(slot, []).append(med.lineId)
        for slot in SLOTS:
            if slot in by_slot:
                doses.append(Dose(
                    doseId="%s#%s#%s" % (plan.circleId, day.isoformat(), slot),
                    date=day.isoformat(), slot=slot,
                    medicineLineIds=sorted(by_slot[slot])))
    return doses
