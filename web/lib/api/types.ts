export type Slot = "morning" | "noon" | "night" | "bedtime";
export type FoodRelation = "before" | "after" | "unspecified";
export type PlanStatus = "draft" | "active" | "archived";
export type DoseStatus = "pending" | "given" | "missed";
export type BoxCheckVerdict = "matched" | "check" | "do_not_take";
export type Role = "owner" | "caregiver";
export type Language = "en" | "hi" | "kn";

export type ApiErrorCode =
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "validation_failed"
  | "extraction_failed"
  | "conflict"
  | "auth_unavailable";

export type ApiError = {
  code: ApiErrorCode;
  message: string;
  details?: Record<string, unknown>;
};

export type Molecule = {
  name: string;
  strengthMg: number | null;
  unit?: "mg" | "iu" | "ml";
};

export type Crop = {
  x: number;
  y: number;
  w: number;
  h: number;
  s3Key?: string;
};

export type Medicine = {
  lineId: string;
  rawText: string;
  brand: string | null;
  molecules: Molecule[];
  form: "tablet" | "capsule" | "syrup" | "injection" | "drops" | "inhaler" | "ointment" | null;
  frequency: string | null;
  slots: Slot[];
  foodRelation: FoodRelation;
  durationDays: number | null;
  prn: boolean;
  prnCondition: string | null;
  confidence: number;
  sourceBlockIds: string[];
  source?: "textract" | "vision_only" | "user";
  needsConfirmation: boolean;
  crop: Crop | null;
};

export type RedFlags = {
  source: "document" | "generic";
  text: string;
  sourceBlockIds?: string[];
};

export type FollowUp = {
  date: string | null;
  with: string | null;
  confidence?: number;
};

export type SlotTimes = {
  morning: string;
  noon: string;
  night: string;
  bedtime: string;
};

export type Plan = {
  planId: string;
  circleId: string;
  patientName: string | null;
  sourceDocumentIds: string[];
  medicines: Medicine[];
  redFlags: RedFlags;
  followUp: FollowUp | null;
  slotTimes: SlotTimes;
  language: Language;
  status: PlanStatus;
};

export type Dose = {
  doseId: string;
  date: string;
  slot: Slot;
  status: DoseStatus;
  givenAt: string | null;
  givenBy: string | null;
  medicineLineIds: string[];
};

export type Adherence = {
  doses: Dose[];
  givenPct: number;
};

export type BoxCheckItem = {
  verdict: BoxCheckVerdict;
  reason: string;
  message: string;
  prescribedLineId: string | null;
  stripBrandText: string | null;
  stripMolecules: Molecule[];
};

export type DocumentUploads = {
  documentId: string;
  uploads: { page: number; uploadUrl: string; key: string }[];
};

export type ActivateResponse = {
  planId: string;
  status: "active";
  dosesCreated: number;
  firstDoseAt: string | null;
};

export type Circle = {
  circleId: string;
  name: string | null;
  language: Language;
  slotTimes: SlotTimes;
  escalationMinutes: number;
  activePlanId: string | null;
  role: Role;
};

export type Invite = {
  token: string;
  url: string;
  expiresAt: string;
};

export type JoinResponse = {
  sessionToken: string;
  role: "caregiver";
  circleId: string;
};

export type AudioClip = {
  url: string;
  spokenLanguage: "en" | "hi";
  text: string;
};

export type PushSubscriptionJSON = {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
};
