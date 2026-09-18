from dataclasses import dataclass, field, fields, asdict
from typing import List, Optional

SLOTS = ("morning", "noon", "night", "bedtime")
DEFAULT_SLOT_TIMES = {"morning": "08:00", "noon": "14:00", "night": "20:00", "bedtime": "22:00"}


@dataclass
class Molecule:
    name: str
    strengthMg: Optional[float] = None
    unit: str = "mg"


@dataclass
class Medicine:
    lineId: str
    rawText: str
    molecules: List[Molecule] = field(default_factory=list)
    brand: Optional[str] = None
    form: Optional[str] = None
    frequency: Optional[str] = None
    slots: List[str] = field(default_factory=list)
    foodRelation: str = "unspecified"
    durationDays: Optional[int] = None
    prn: bool = False
    prnCondition: Optional[str] = None
    confidence: float = 0.0
    sourceBlockIds: List[str] = field(default_factory=list)
    source: str = "textract"
    needsConfirmation: bool = True
    crop: Optional[dict] = None


@dataclass
class RedFlags:
    source: str  # "document" | "generic"
    text: str
    sourceBlockIds: List[str] = field(default_factory=list)


@dataclass
class Plan:
    planId: str
    circleId: str
    medicines: List[Medicine] = field(default_factory=list)
    redFlags: Optional[RedFlags] = None
    patientName: Optional[str] = None
    sourceDocumentIds: List[str] = field(default_factory=list)
    followUp: Optional[dict] = None
    slotTimes: dict = field(default_factory=lambda: dict(DEFAULT_SLOT_TIMES))
    language: str = "en"
    status: str = "draft"

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d):
        """Tolerates a DynamoDB round trip: numbers as strings, unknown keys ignored."""
        meds = [_medicine(m) for m in d.get("medicines", [])]
        rf = d.get("redFlags")
        return Plan(
            planId=d["planId"], circleId=d["circleId"], medicines=meds,
            redFlags=RedFlags(**_known(RedFlags, rf)) if rf else None,
            patientName=d.get("patientName"),
            sourceDocumentIds=d.get("sourceDocumentIds", []),
            followUp=d.get("followUp"),
            slotTimes=d.get("slotTimes", dict(DEFAULT_SLOT_TIMES)),
            language=d.get("language", "en"), status=d.get("status", "draft"))


def _known(cls, d):
    names = {f.name for f in fields(cls)}
    return {k: v for k, v in d.items() if k in names}


def _opt(convert, value):
    return None if value is None else convert(value)


def _medicine(d):
    m = Medicine(**_known(Medicine, d))
    m.lineId = str(m.lineId)
    m.molecules = [Molecule(**_known(Molecule, x)) for x in d.get("molecules", [])]
    for x in m.molecules:
        x.strengthMg = _opt(float, x.strengthMg)
    m.confidence = _opt(float, m.confidence)
    m.durationDays = _opt(lambda v: int(float(v)), m.durationDays)
    if m.crop:
        m.crop = {k: (_opt(float, v) if k in ("x", "y", "w", "h") else v)
                  for k, v in m.crop.items()}
    return m


@dataclass
class Dose:
    doseId: str
    date: str
    slot: str
    status: str = "pending"
    givenAt: Optional[str] = None
    givenBy: Optional[str] = None
    medicineLineIds: List[str] = field(default_factory=list)
