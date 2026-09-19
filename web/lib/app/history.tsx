"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

type HistoryContextValue = {
  canBack: boolean;
  canForward: boolean;
  back: () => void;
  forward: () => void;
};

const HistoryContext = createContext<HistoryContextValue | null>(null);

function canon(path: string) {
  if (!path || path === "/") return "/";
  return path.endsWith("/") ? path.slice(0, -1) : path;
}

export function AppHistoryProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const stack = useRef<string[]>([]);
  const index = useRef(-1);
  const jumping = useRef(false);
  const [canBack, setCanBack] = useState(false);
  const [canForward, setCanForward] = useState(false);

  const sync = useCallback(() => {
    setCanBack(index.current > 0);
    setCanForward(index.current >= 0 && index.current < stack.current.length - 1);
  }, []);

  useEffect(() => {
    const path = canon(pathname);

    if (jumping.current) {
      jumping.current = false;
      if (stack.current[index.current] !== path) {
        const prev = index.current - 1;
        const next = index.current + 1;
        if (stack.current[prev] === path) index.current = prev;
        else if (stack.current[next] === path) index.current = next;
        else {
          const found = stack.current.lastIndexOf(path);
          if (found >= 0) index.current = found;
        }
      }
      sync();
      return;
    }

    if (stack.current[index.current] === path) {
      sync();
      return;
    }

    stack.current = stack.current.slice(0, index.current + 1);
    stack.current.push(path);
    index.current = stack.current.length - 1;
    sync();
  }, [pathname, sync]);

  const back = useCallback(() => {
    if (index.current <= 0) return;
    jumping.current = true;
    index.current -= 1;
    router.push(stack.current[index.current]);
    sync();
  }, [router, sync]);

  const forward = useCallback(() => {
    if (index.current >= stack.current.length - 1) return;
    jumping.current = true;
    index.current += 1;
    router.push(stack.current[index.current]);
    sync();
  }, [router, sync]);

  const value = useMemo(() => ({ canBack, canForward, back, forward }), [canBack, canForward, back, forward]);

  return <HistoryContext.Provider value={value}>{children}</HistoryContext.Provider>;
}

export function useAppHistory() {
  const context = useContext(HistoryContext);
  if (!context) throw new Error("useAppHistory must be used inside AppHistoryProvider");
  return context;
}
