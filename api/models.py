from dataclasses import dataclass, field, asdict
from typing import List, Optional

SLOTS = ("morning", "noon", "night", "bedtime")


@dataclass
class Molecule:
    name: str
    strengthMg: Optional[float] = None


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
    slotTimes: dict = field(default_factory=lambda: {
        "morning": "08:00", "noon": "14:00", "night": "20:00", "bedtime": "22:00"})
    language: str = "en"
    status: str = "draft"

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d):
        meds = [Medicine(**{**m, "molecules": [Molecule(**x) for x in m.get("molecules", [])]})
                for m in d.get("medicines", [])]
        rf = d.get("redFlags")
        return Plan(
            planId=d["planId"], circleId=d["circleId"], medicines=meds,
            redFlags=RedFlags(**rf) if rf else None,
            patientName=d.get("patientName"),
            sourceDocumentIds=d.get("sourceDocumentIds", []),
            followUp=d.get("followUp"),
            slotTimes=d.get("slotTimes", Plan(planId="", circleId="").slotTimes),
            language=d.get("language", "en"), status=d.get("status", "draft"))


@dataclass
class Dose:
    doseId: str
    date: str
    slot: str
    status: str = "pending"
    givenAt: Optional[str] = None
    givenBy: Optional[str] = None
    medicineLineIds: List[str] = field(default_factory=list)
