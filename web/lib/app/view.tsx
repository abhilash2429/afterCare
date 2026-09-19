"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";

const STORAGE_KEY = "aftercare-view";

export type SiteView = "web" | "app";

type AppViewContextValue = {
  view: SiteView;
  isApp: boolean;
  enterApp: () => void;
  enterWeb: () => void;
};

const AppViewContext = createContext<AppViewContextValue | null>(null);

function pathIsAppHome(pathname: string) {
  return pathname === "/app" || pathname === "/app/";
}

function readStoredView(): SiteView {
  if (typeof window === "undefined") return "web";
  if (pathIsAppHome(window.location.pathname)) return "app";
  return window.sessionStorage.getItem(STORAGE_KEY) === "app" ? "app" : "web";
}

export function AppViewProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [view, setView] = useState<SiteView>("web");

  useEffect(() => {
    setView(readStoredView());
  }, []);

  const enterApp = useCallback(() => {
    window.sessionStorage.setItem(STORAGE_KEY, "app");
    setView("app");
  }, []);

  const enterWeb = useCallback(() => {
    window.sessionStorage.setItem(STORAGE_KEY, "web");
    setView("web");
  }, []);

  useEffect(() => {
    if (pathIsAppHome(pathname)) enterApp();
  }, [pathname, enterApp]);

  const value = useMemo(
    () => ({ view, isApp: view === "app" || pathIsAppHome(pathname), enterApp, enterWeb }),
    [view, pathname, enterApp, enterWeb],
  );

  return <AppViewContext.Provider value={value}>{children}</AppViewContext.Provider>;
}

export function useAppView() {
  const context = useContext(AppViewContext);
  if (!context) throw new Error("useAppView must be used inside AppViewProvider");
  return context;
}

export function isAppHomePath(pathname: string) {
  return pathIsAppHome(pathname);
}
