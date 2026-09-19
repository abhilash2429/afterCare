"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { api, ApiRequestError, putPresigned } from "@/lib/api/client";
import type {
  AudioClip,
  BoxCheckItem,
  Circle,
  Dose,
  Invite,
  Medicine,
  Plan,
  Role,
  Slot,
} from "@/lib/api/types";
import { isDemoMode } from "@/lib/app/mode";
import { explainError, EXTRACTION_FAILED, INVITE_USED } from "@/lib/app/errors";
import { configureAuth, getIdToken, ownerSignOut } from "@/lib/auth/cognito";
import { clearSession, getSession, patchSession, setSession } from "@/lib/auth/session";
import { DEMO_BOX_CHECK, DEMO_PLAN, dosesForPlan, EXTRACT_STEPS } from "@/lib/demo/fixtures";
import { imageTypeOf, sharedImageType, type ImageType } from "@/lib/media/files";
import {
  cacheDosesJson,
  cachePlanJson,
  clearCaches,
  loadCachedDosesJson,
  loadCachedPlanJson,
  notifyWorkerToCachePlan,
} from "@/lib/offline/cache";
import { dequeueGiven, enqueueGiven, loadQueue } from "@/lib/offline/queue";
import { apiLang, asUiLang, type UiLang } from "@/lib/copy";
import { todayIst } from "@/lib/format";

export type PageFile = {
  id: string;
  name: string;
  previewUrl: string;
  file: File;
  contentType: ImageType;
};

type AppState = {
  ready: boolean;
  demo: boolean;
  role: Role | null;
  circleId: string | null;
  planId: string | null;
  circle: Circle | null;
  plan: Plan | null;
  doses: Dose[];
  weekDoses: Dose[];
  givenPct: number | null;
  pages: PageFile[];
  stripPages: PageFile[];
  extracting: boolean;
  extractStep: string;
  boxChecking: boolean;
  boxCheckItems: BoxCheckItem[] | null;
  queuedDoseIds: string[];
  audio: AudioClip | null;
  error: string | null;
  uiLang: UiLang;
};

type AppContextValue = AppState & {
  signedIn: boolean;
  addPages: (files: FileList | File[], target?: "pages" | "strips") => string | null;
  removePage: (id: string, target?: "pages" | "strips") => void;
  startExtract: () => Promise<boolean>;
  confirmMedicine: (lineId: string) => Promise<boolean>;
  saveMedicines: (medicines: Medicine[], userEdited: boolean) => Promise<boolean>;
  activate: () => Promise<boolean>;
  markGiven: (doseId: string) => Promise<void>;
  runBoxCheck: () => Promise<boolean>;
  refresh: () => Promise<void>;
  loadAudio: () => Promise<AudioClip | null>;
  createCircle: (name: string, language: UiLang) => Promise<string | null>;
  inviteCaregiver: () => Promise<Invite | null>;
  joinInvite: (circleId: string, token: string) => Promise<boolean>;
  signOutAll: () => Promise<void>;
  reset: () => void;
  setError: (message: string | null) => void;
  setUiLang: (language: UiLang) => void;
  unlockOwner: () => void;
};

const AppContext = createContext<AppContextValue | null>(null);

function newPage(file: File, contentType: ImageType): PageFile {
  return {
    id: `${file.name}-${file.lastModified}-${file.size}-${crypto.randomUUID()}`,
    name: file.name,
    previewUrl: URL.createObjectURL(file),
    file,
    contentType,
  };
}

function todayDoses(doses: Dose[]): Dose[] {
  const today = todayIst();
  return doses.filter((dose) => dose.date === today);
}

export function AppProvider({ children }: { children: ReactNode }) {
  const demo = isDemoMode();
  const [ready, setReady] = useState(false);
  const [role, setRole] = useState<Role | null>(null);
  const [circleId, setCircleId] = useState<string | null>(null);
  const [planId, setPlanId] = useState<string | null>(null);
  const [circle, setCircle] = useState<Circle | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [doses, setDoses] = useState<Dose[]>([]);
  const [weekDoses, setWeekDoses] = useState<Dose[]>([]);
  const [givenPct, setGivenPct] = useState<number | null>(null);
  const [pages, setPages] = useState<PageFile[]>([]);
  const [stripPages, setStripPages] = useState<PageFile[]>([]);
  const [extracting, setExtracting] = useState(false);
  const [extractStep, setExtractStep] = useState("Reading the prescription...");
  const [boxChecking, setBoxChecking] = useState(false);
  const [boxCheckItems, setBoxCheckItems] = useState<BoxCheckItem[] | null>(null);
  const [queuedDoseIds, setQueuedDoseIds] = useState<string[]>([]);
  const [audio, setAudio] = useState<AudioClip | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uiLang, setUiLangState] = useState<UiLang>("en");
  const [ownerAuthed, setOwnerAuthed] = useState(false);
  const [localAccess, setLocalAccess] = useState(false);
  const flushing = useRef(false);
  const refreshRef = useRef<() => Promise<void>>(async () => {});

  const persistPlan = useCallback((next: Plan | null) => {
    setPlan(next);
    if (next) {
      cachePlanJson(JSON.stringify(next));
      patchSession({ planId: next.planId, circleId: next.circleId });
      setPlanId(next.planId);
      notifyWorkerToCachePlan();
    }
  }, []);

  const persistDoses = useCallback((next: Dose[], pct?: number | null) => {
    setDoses(todayDoses(next));
    setWeekDoses(next);
    if (pct !== undefined) setGivenPct(pct);
    cacheDosesJson(JSON.stringify({ doses: next, givenPct: pct ?? null }));
  }, []);

  const refresh = useCallback(async () => {
    if (demo) {
      const session = getSession();
      setRole(session?.role ?? null);
      setOwnerAuthed(false);
      setCircleId(session?.circleId ?? null);
      setPlanId(session?.planId ?? null);
      setQueuedDoseIds(loadQueue().map((item) => item.doseId));
      return;
    }

    configureAuth();
    const idToken = await getIdToken();
    const session = getSession();
    const sessionLocal = Boolean(session?.localAccess);
    setLocalAccess(sessionLocal);
    setOwnerAuthed(Boolean(idToken) || sessionLocal);
    const nextRole: Role | null = session?.role ?? (idToken || sessionLocal ? "owner" : null);
    setRole(nextRole);
    const cid = session?.circleId ?? null;
    setCircleId(cid);
    if (!cid || (!idToken && nextRole !== "caregiver" && !sessionLocal)) {
      setCircle(null);
      return;
    }
    if (sessionLocal && !idToken) {
      return;
    }
    try {
      const nextCircle = await api.getCircle(cid);
      setCircle(nextCircle);
      setRole(nextCircle.role);
      const nextPlanId = nextCircle.activePlanId ?? session?.planId ?? null;
      setPlanId(nextPlanId);
      const stored = getSession()?.language ?? session?.language ?? null;
      if (stored) {
        const nextUi = asUiLang(stored);
        setUiLangState(nextUi);
        patchSession({
          circleId: cid,
          planId: nextPlanId,
          role: nextCircle.role,
          language: nextUi,
        });
      } else {
        patchSession({
          circleId: cid,
          planId: nextPlanId,
          role: nextCircle.role,
        });
      }
      if (!nextPlanId) return;
      const [nextPlan, adherence] = await Promise.all([
        api.getPlan(nextPlanId, cid),
        api.adherence(nextPlanId, 7, cid).catch(() => null),
      ]);
      persistPlan(nextPlan);
      if (adherence) {
        persistDoses(adherence.doses, adherence.givenPct);
      }
    } catch (err) {
      setError(explainError(err, "Loading this circle"));
    }
  }, [demo, persistDoses, persistPlan]);

  const flushQueue = useCallback(async () => {
    if (demo || localAccess || flushing.current || !navigator.onLine) return;
    const queued = loadQueue();
    if (queued.length === 0) return;
    flushing.current = true;
    try {
      for (const item of queued) {
        try {
          await api.markGiven(item.doseId);
          const remaining = dequeueGiven(item.doseId);
          setQueuedDoseIds(remaining.map((entry) => entry.doseId));
        } catch (err) {
          if (err instanceof ApiRequestError && (err.code === "not_found" || err.code === "forbidden")) {
            const remaining = dequeueGiven(item.doseId);
            setQueuedDoseIds(remaining.map((entry) => entry.doseId));
          }
        }
      }
      if (planId && circleId) {
        const adherence = await api.adherence(planId, 7, circleId);
        persistDoses(adherence.doses, adherence.givenPct);
      }
    } finally {
      flushing.current = false;
    }
  }, [circleId, demo, localAccess, persistDoses, planId]);

  useEffect(() => {
    const cachedPlan = loadCachedPlanJson();
    const cachedDoses = loadCachedDosesJson();
    if (cachedPlan) {
      try {
        const parsed = JSON.parse(cachedPlan) as Plan;
        setPlan(parsed);
        setPlanId(parsed.planId);
        setCircleId(parsed.circleId);
      } catch {
        // Ignore a broken cache.
      }
    }
    if (cachedDoses) {
      try {
        const parsed = JSON.parse(cachedDoses) as { doses: Dose[]; givenPct: number | null };
        persistDoses(parsed.doses, parsed.givenPct);
      } catch {
        // Ignore a broken cache.
      }
    }
    const session = getSession();
    if (session) {
      setRole(session.role);
      setCircleId(session.circleId);
      setPlanId(session.planId);
      if (session.language) setUiLangState(session.language);
      if (session.localAccess) {
        setLocalAccess(true);
        setOwnerAuthed(true);
      }
    }
    setQueuedDoseIds(loadQueue().map((item) => item.doseId));
    void refresh().finally(() => setReady(true));
    // First paint hydrates from localStorage, then refresh() talks to the API.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    function onOnline() {
      void flushQueue();
      void refresh();
    }
    refreshRef.current = refresh;
    window.addEventListener("online", onOnline);
    return () => window.removeEventListener("online", onOnline);
  }, [flushQueue, refresh]);

  const addPages = useCallback((files: FileList | File[], target: "pages" | "strips" = "pages") => {
    const incoming = Array.from(files);
    const typed = incoming.filter((file) => imageTypeOf(file));
    if (typed.length === 0) return "Use a JPEG or PNG photo.";
    const current = target === "strips" ? stripPages : pages;
    const combined = [...current.map((page) => page.file), ...typed];
    if (combined.length > 10) return "Use up to 10 pages.";
    if (!sharedImageType(combined)) return "All pages need to be JPEG, or all PNG. Not both.";
    const additions = typed.map((file) => newPage(file, imageTypeOf(file) as ImageType));
    if (target === "strips") setStripPages((cur) => [...cur, ...additions]);
    else setPages((cur) => [...cur, ...additions]);
    return null;
  }, [pages, stripPages]);

  const removePage = useCallback((id: string, target: "pages" | "strips" = "pages") => {
    const update = (current: PageFile[]) => {
      const found = current.find((page) => page.id === id);
      if (found) URL.revokeObjectURL(found.previewUrl);
      return current.filter((page) => page.id !== id);
    };
    if (target === "strips") setStripPages(update);
    else setPages(update);
  }, []);

  const startExtract = useCallback(async () => {
    setError(null);
    if (demo || localAccess) {
      setExtracting(true);
      for (const step of EXTRACT_STEPS) {
        setExtractStep(step);
        await new Promise((resolve) => setTimeout(resolve, 700));
      }
      persistPlan({
        ...DEMO_PLAN,
        circleId: circleId ?? DEMO_PLAN.circleId,
        status: "draft",
      });
      persistDoses([]);
      setBoxCheckItems(null);
      setExtracting(false);
      return true;
    }
    if (!circleId) {
      setError("Create a care circle first.");
      return false;
    }
    if (pages.length === 0) {
      setError("Photograph at least one page of the discharge summary.");
      return false;
    }
    const contentType = sharedImageType(pages.map((page) => page.file));
    if (!contentType) {
      setError("All pages need to be JPEG, or all PNG. Not both.");
      return false;
    }
    setExtracting(true);
    setExtractStep("Reading the prescription...");
    try {
      const created = await api.createDocument({
        circleId,
        pageCount: pages.length,
        contentType,
      });
      for (const upload of created.uploads) {
        const page = pages[upload.page - 1];
        if (!page) continue;
        await putPresigned(upload.uploadUrl, page.file, contentType);
      }
      const next = await api.extract(created.documentId, circleId);
      persistPlan(next);
      persistDoses([]);
      setBoxCheckItems(null);
      return true;
    } catch (err) {
      if (err instanceof ApiRequestError && err.code === "extraction_failed") {
        setError(EXTRACTION_FAILED);
      } else {
        setError(explainError(err, "Reading the prescription"));
      }
      return false;
    } finally {
      setExtracting(false);
    }
  }, [circleId, demo, localAccess, pages, persistDoses, persistPlan]);

  const saveMedicines = useCallback(
    async (medicines: Medicine[], userEdited: boolean) => {
      if (!plan) return false;
      if (demo || localAccess) {
        persistPlan({ ...plan, medicines });
        return true;
      }
      try {
        const next = await api.patchPlan(plan.planId, {
          circleId: plan.circleId,
          medicines,
          userEdited,
          language: plan.language,
          slotTimes: plan.slotTimes,
        });
        persistPlan(next);
        setError(null);
        return true;
      } catch (err) {
        setError(explainError(err, "Saving the plan"));
        return false;
      }
    },
    [demo, localAccess, persistPlan, plan],
  );

  const confirmMedicine = useCallback(
    async (lineId: string) => {
      if (!plan) return false;
      const medicines = plan.medicines.map((medicine) =>
        medicine.lineId === lineId ? { ...medicine, needsConfirmation: false } : medicine,
      );
      return saveMedicines(medicines, false);
    },
    [plan, saveMedicines],
  );

  const activate = useCallback(async () => {
    if (!plan) return false;
    if (plan.medicines.some((medicine) => medicine.needsConfirmation)) return false;
    if (demo || localAccess) {
      const next = { ...plan, status: "active" as const };
      persistPlan(next);
      persistDoses(dosesForPlan(next), 0);
      return true;
    }
    try {
      await api.activatePlan(plan.planId, plan.circleId);
      await refresh();
      return true;
    } catch (err) {
      if (err instanceof ApiRequestError && err.code === "conflict") {
        await refresh();
        return true;
      }
      setError(explainError(err, "Activating the schedule"));
      return false;
    }
  }, [demo, localAccess, persistDoses, persistPlan, plan, refresh]);

  const markGiven = useCallback(
    async (doseId: string) => {
      const applyLocal = () => {
        persistDoses(
          weekDoses.map((dose) =>
            dose.doseId === doseId
              ? { ...dose, status: "given", givenAt: new Date().toISOString(), givenBy: role }
              : dose,
          ),
          givenPct,
        );
      };
      if (demo || localAccess) {
        applyLocal();
        return;
      }
      if (!navigator.onLine) {
        applyLocal();
        setQueuedDoseIds(enqueueGiven(doseId).map((item) => item.doseId));
        return;
      }
      try {
        await api.markGiven(doseId);
        applyLocal();
        if (planId && circleId) {
          const adherence = await api.adherence(planId, 1, circleId);
          persistDoses(
            [...adherence.doses, ...weekDoses.filter((dose) => dose.date !== todayIst())],
            adherence.givenPct,
          );
        }
      } catch (err) {
        applyLocal();
        setQueuedDoseIds(enqueueGiven(doseId).map((item) => item.doseId));
        if (!(err instanceof TypeError)) {
          setError(explainError(err, "Marking this dose given"));
        }
      }
    },
    [circleId, demo, givenPct, localAccess, persistDoses, planId, role, weekDoses],
  );

  const runBoxCheck = useCallback(async () => {
    setError(null);
    if (demo || localAccess) {
      setBoxChecking(true);
      setExtractStep("Checking the strips...");
      await new Promise((resolve) => setTimeout(resolve, 800));
      setBoxCheckItems(DEMO_BOX_CHECK);
      setBoxChecking(false);
      return true;
    }
    if (!circleId || !planId) {
      setError("Activate a plan first.");
      return false;
    }
    if (stripPages.length === 0) {
      setError("Photograph the strips in the box.");
      return false;
    }
    const contentType = sharedImageType(stripPages.map((page) => page.file));
    if (!contentType) {
      setError("All strip photos need to be JPEG, or all PNG. Not both.");
      return false;
    }
    setBoxChecking(true);
    try {
      const created = await api.createDocument({
        circleId,
        pageCount: stripPages.length,
        contentType,
      });
      for (const upload of created.uploads) {
        const page = stripPages[upload.page - 1];
        if (!page) continue;
        await putPresigned(upload.uploadUrl, page.file, contentType);
      }
      const result = await api.boxCheck({ circleId, planId, documentId: created.documentId });
      setBoxCheckItems(result.items);
      return true;
    } catch (err) {
      setError(explainError(err, "Checking the box"));
      return false;
    } finally {
      setBoxChecking(false);
    }
  }, [circleId, demo, localAccess, planId, stripPages]);

  const loadAudio = useCallback(async () => {
    if (!plan) return null;
    if (demo || localAccess) {
      const clip: AudioClip = {
        url: "",
        spokenLanguage: "hi",
        text: plan.medicines.map((medicine) => medicine.brand ?? medicine.rawText).join(". "),
      };
      setAudio(clip);
      return clip;
    }
    try {
      const clip = await api.audio(plan.planId, apiLang(uiLang), plan.circleId);
      setAudio(clip);
      return clip;
    } catch (err) {
      setError(explainError(err, "Loading the spoken schedule"));
      return null;
    }
  }, [demo, localAccess, plan, uiLang]);

  const createCircle = useCallback(async (name: string, language: UiLang) => {
    setError(null);
    const apiLanguage = apiLang(language);
    const local = demo || getSession()?.localAccess;
    if (local) {
      const id = getSession()?.circleId ?? `ci_local_${crypto.randomUUID().slice(0, 8)}`;
      setCircleId(id);
      setRole("owner");
      setOwnerAuthed(true);
      setLocalAccess(true);
      setUiLangState(language);
      setSession({
        role: "owner",
        circleId: id,
        planId: null,
        caregiverToken: null,
        language,
        localAccess: true,
      });
      return id;
    }
    try {
      const created = await api.createCircle({ name, language: apiLanguage });
      setCircleId(created.circleId);
      setRole("owner");
      setUiLangState(language);
      setSession({
        role: "owner",
        circleId: created.circleId,
        planId: null,
        caregiverToken: null,
        language,
      });
      await refresh();
      return created.circleId;
    } catch (err) {
      setError(explainError(err, "Creating the circle"));
      return null;
    }
  }, [demo, refresh]);

  const inviteCaregiver = useCallback(async () => {
    if (!circleId) {
      setError("Create a care circle first.");
      return null;
    }
    if (demo || getSession()?.localAccess) {
      const token = "demo-invite";
      return {
        token,
        url: `${window.location.origin}/join/?c=${circleId}&t=${token}`,
        expiresAt: new Date(Date.now() + 24 * 3600 * 1000).toISOString(),
      };
    }
    try {
      return await api.invite(circleId);
    } catch (err) {
      setError(explainError(err, "Creating an invite"));
      return null;
    }
  }, [circleId, demo]);

  const joinInvite = useCallback(async (joinCircleId: string, token: string) => {
    setError(null);
    if (demo || localAccess || token === "demo-invite") {
      setSession({
        role: "caregiver",
        circleId: joinCircleId,
        planId: DEMO_PLAN.planId,
        caregiverToken: "demo-caregiver-session",
        language: "kn",
        localAccess: true,
      });
      persistPlan({ ...DEMO_PLAN, status: "active" });
      persistDoses(dosesForPlan({ ...DEMO_PLAN, status: "active" }), 0);
      setRole("caregiver");
      setCircleId(joinCircleId);
      setUiLangState("kn");
      return true;
    }
    try {
      const joined = await api.joinCircle(joinCircleId, token);
      setSession({
        role: "caregiver",
        circleId: joined.circleId,
        planId: null,
        caregiverToken: joined.sessionToken,
        language: null,
      });
      setRole("caregiver");
      setCircleId(joined.circleId);
      await refresh();
      return true;
    } catch (err) {
      if (err instanceof ApiRequestError && err.code === "not_found") {
        setError(INVITE_USED);
      } else {
        setError(explainError(err, "Joining this circle"));
      }
      return false;
    }
  }, [demo, localAccess, persistDoses, persistPlan, refresh]);

  const setUiLang = useCallback((language: UiLang) => {
    setUiLangState(language);
    patchSession({ language });
  }, []);

  const unlockOwner = useCallback(() => {
    setOwnerAuthed(true);
    setLocalAccess(true);
    setRole("owner");
    setError(null);
    patchSession({ role: "owner", localAccess: true });
  }, []);

  const signOutAll = useCallback(async () => {
    await ownerSignOut();
    clearSession();
    clearCaches();
    setRole(null);
    setCircleId(null);
    setPlanId(null);
    setCircle(null);
    setPlan(null);
    setDoses([]);
    setWeekDoses([]);
    setGivenPct(null);
    setBoxCheckItems(null);
    setAudio(null);
    setUiLangState("en");
    setOwnerAuthed(false);
    setLocalAccess(false);
  }, []);

  const reset = useCallback(() => {
    pages.forEach((page) => URL.revokeObjectURL(page.previewUrl));
    stripPages.forEach((page) => URL.revokeObjectURL(page.previewUrl));
    setPages([]);
    setStripPages([]);
    setBoxCheckItems(null);
    setError(null);
    if (demo || localAccess) {
      persistPlan(null);
      persistDoses([]);
      clearCaches();
      clearSession();
    }
  }, [demo, localAccess, pages, persistDoses, persistPlan, stripPages]);

  const value = useMemo<AppContextValue>(
    () => ({
      ready,
      demo,
      role,
      circleId,
      planId,
      circle,
      plan,
      doses,
      weekDoses,
      givenPct,
      pages,
      stripPages,
      extracting,
      extractStep,
      boxChecking,
      boxCheckItems,
      queuedDoseIds,
      audio,
      error,
      uiLang,
      signedIn: Boolean(ownerAuthed || localAccess || (role === "caregiver" && circleId) || (demo && circleId)),
      addPages,
      removePage,
      startExtract,
      confirmMedicine,
      saveMedicines,
      activate,
      markGiven,
      runBoxCheck,
      refresh,
      loadAudio,
      createCircle,
      inviteCaregiver,
      joinInvite,
      signOutAll,
      reset,
      setError,
      setUiLang,
      unlockOwner,
    }),
    [
      activate,
      addPages,
      audio,
      boxCheckItems,
      boxChecking,
      circle,
      circleId,
      confirmMedicine,
      createCircle,
      demo,
      doses,
      error,
      extractStep,
      extracting,
      givenPct,
      inviteCaregiver,
      joinInvite,
      loadAudio,
      markGiven,
      ownerAuthed,
      localAccess,
      pages,
      plan,
      planId,
      queuedDoseIds,
      ready,
      refresh,
      removePage,
      reset,
      role,
      runBoxCheck,
      saveMedicines,
      signOutAll,
      startExtract,
      stripPages,
      setUiLang,
      unlockOwner,
      uiLang,
      weekDoses,
    ],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used inside AppProvider");
  return context;
}

export function emptyUserMedicine(slots: Slot[] = []): Medicine {
  return {
    lineId: `u_${crypto.randomUUID().slice(0, 8)}`,
    rawText: "",
    brand: null,
    molecules: [],
    form: null,
    frequency: null,
    slots,
    foodRelation: "unspecified",
    durationDays: null,
    prn: false,
    prnCondition: null,
    confidence: 1,
    sourceBlockIds: [],
    source: "user",
    needsConfirmation: false,
    crop: null,
  };
}
