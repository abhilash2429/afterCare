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
import type { BoxCheckItem, Dose, Plan } from "@/lib/api/types";
import { DEMO_BOX_CHECK, DEMO_PLAN, dosesForPlan, EXTRACT_STEPS } from "@/lib/demo/fixtures";

export type UploadPage = {
  id: string;
  name: string;
  previewUrl: string;
};

type Persisted = {
  plan: Plan | null;
  doses: Dose[];
  confirmedLineIds: string[];
  userEdited: boolean;
  boxCheckItems: BoxCheckItem[] | null;
};

const STORAGE_KEY = "aftercare-demo-v1";

const empty: Persisted = {
  plan: null,
  doses: [],
  confirmedLineIds: [],
  userEdited: false,
  boxCheckItems: null,
};

type DemoContextValue = Persisted & {
  ready: boolean;
  pages: UploadPage[];
  extracting: boolean;
  extractStep: string;
  addPages: (files: FileList | File[]) => void;
  removePage: (id: string) => void;
  startExtract: () => Promise<void>;
  confirmMedicine: (lineId: string) => void;
  activate: () => boolean;
  markGiven: (doseId: string) => void;
  runBoxCheck: () => void;
  reset: () => void;
};

const DemoContext = createContext<DemoContextValue | null>(null);

function load(): Persisted {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return empty;
    return { ...empty, ...(JSON.parse(raw) as Persisted) };
  } catch {
    return empty;
  }
}

function save(state: Persisted) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

export function DemoProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [state, setState] = useState<Persisted>(empty);
  const [pages, setPages] = useState<UploadPage[]>([]);
  const [extracting, setExtracting] = useState(false);
  const [extractStep, setExtractStep] = useState(EXTRACT_STEPS[0]);
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    setState(load());
    setReady(true);
  }, []);

  const update = useCallback((patch: Partial<Persisted> | ((current: Persisted) => Persisted)) => {
    setState((current) => {
      const next = typeof patch === "function" ? patch(current) : { ...current, ...patch };
      save(next);
      return next;
    });
  }, []);

  const addPages = useCallback((files: FileList | File[]) => {
    const incoming = Array.from(files).filter((file) => file.type.startsWith("image/"));
    setPages((current) => [
      ...current,
      ...incoming.map((file) => ({
        id: `${file.name}-${file.lastModified}-${file.size}`,
        name: file.name,
        previewUrl: URL.createObjectURL(file),
      })),
    ]);
  }, []);

  const removePage = useCallback((id: string) => {
    setPages((current) => {
      const target = current.find((page) => page.id === id);
      if (target) URL.revokeObjectURL(target.previewUrl);
      return current.filter((page) => page.id !== id);
    });
  }, []);

  const startExtract = useCallback(async () => {
    setExtracting(true);
    for (const step of EXTRACT_STEPS) {
      setExtractStep(step);
      await new Promise((resolve) => setTimeout(resolve, 700));
    }
    update({
      plan: { ...DEMO_PLAN, status: "draft" },
      doses: [],
      confirmedLineIds: DEMO_PLAN.medicines
        .filter((medicine) => !medicine.needsConfirmation)
        .map((medicine) => medicine.lineId),
      userEdited: false,
      boxCheckItems: null,
    });
    setExtracting(false);
  }, [update]);

  const confirmMedicine = useCallback(
    (lineId: string) => {
      update((current) => ({
        ...current,
        confirmedLineIds: current.confirmedLineIds.includes(lineId)
          ? current.confirmedLineIds
          : [...current.confirmedLineIds, lineId],
      }));
    },
    [update],
  );

  const activate = useCallback(() => {
    const current = stateRef.current;
    if (!current.plan) return false;
    const unresolved = current.plan.medicines.filter(
      (medicine) => medicine.needsConfirmation && !current.confirmedLineIds.includes(medicine.lineId),
    );
    if (unresolved.length > 0) return false;
    const plan = { ...current.plan, status: "active" as const };
    update({
      plan,
      doses: dosesForPlan(plan),
    });
    return true;
  }, [update]);

  const markGiven = useCallback(
    (doseId: string) => {
      update((current) => ({
        ...current,
        doses: current.doses.map((dose) =>
          dose.doseId === doseId
            ? {
                ...dose,
                status: "given",
                givenAt: new Date().toISOString(),
                givenBy: "caregiver_demo",
              }
            : dose,
        ),
      }));
    },
    [update],
  );

  const runBoxCheck = useCallback(() => {
    update({ boxCheckItems: DEMO_BOX_CHECK });
  }, [update]);

  const reset = useCallback(() => {
    pages.forEach((page) => URL.revokeObjectURL(page.previewUrl));
    setPages([]);
    update(empty);
  }, [pages, update]);

  const value = useMemo<DemoContextValue>(
    () => ({
      ready,
      pages,
      extracting,
      extractStep,
      ...state,
      addPages,
      removePage,
      startExtract,
      confirmMedicine,
      activate,
      markGiven,
      runBoxCheck,
      reset,
    }),
    [
      ready,
      pages,
      extracting,
      extractStep,
      state,
      addPages,
      removePage,
      startExtract,
      confirmMedicine,
      activate,
      markGiven,
      runBoxCheck,
      reset,
    ],
  );

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}

export function useDemo() {
  const context = useContext(DemoContext);
  if (!context) {
    throw new Error("useDemo must be used inside DemoProvider");
  }
  return context;
}
