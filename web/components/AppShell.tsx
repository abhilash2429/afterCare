"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AppChrome } from "@/components/app/AppChrome";
import { AppHome } from "@/components/app/AppHome";
import { PhoneStage } from "@/components/app/PhoneStage";
import { Bilingual } from "@/components/Bilingual";
import { BtnArrow } from "@/components/Button";
import { BottomNav } from "@/components/BottomNav";
import { Disclaimer } from "@/components/Disclaimer";
import { Footer } from "@/components/Footer";
import { SiteIntro } from "@/components/SiteIntro";
import { TopNav } from "@/components/TopNav";
import { useApp } from "@/lib/app/store";
import { isAppHomePath, useAppView } from "@/lib/app/view";
import { scriptClass } from "@/lib/copy";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const home = pathname === "/";
  const appHome = isAppHomePath(pathname);
  const showHome = home || appHome;
  const seenHome = useRef(showHome);
  if (showHome) seenHome.current = true;
  const { isApp } = useAppView();
  const { authRequired, circleId, demo, setError, uiLang } = useApp();
  const showBottom = Boolean(circleId) && !home && !appHome;

  useEffect(() => {
    setError(null);
  }, [pathname, setError]);

  useEffect(() => {
    document.documentElement.lang = uiLang === "en" ? "en" : uiLang;
  }, [uiLang]);

  useEffect(() => {
    if (authRequired && pathname !== "/setup/") router.push("/setup/");
  }, [authRequired, pathname, router]);

  if (isApp) {
    return (
      <PhoneStage>
        {seenHome.current ? (
          <div className={`appv-pane${showHome ? " is-on" : ""}`} aria-hidden={!showHome} inert={!showHome}>
            <AppHome />
          </div>
        ) : null}
        {showHome ? null : (
          <div className={`appv-shell appv-shell-page ${scriptClass(uiLang)}`}>
            <AppChrome />
            <div className="appv-screen appv-screen-page">
              {children}
              <div className="mt-10 pb-4">
                <Disclaimer />
              </div>
            </div>
            <BottomNav />
          </div>
        )}
      </PhoneStage>
    );
  }

  return (
    <div className={`site ${scriptClass(uiLang)}${home ? " site-home" : ""}${showBottom ? " has-bottom-nav" : ""}`}>
      {home ? <SiteIntro /> : null}
      <header className="site-header print:hidden">
        <Link href="/" className="site-logo">
          AfterCare
        </Link>
        {home ? <TopNav /> : null}
        <div className="site-header-actions">
          {demo ? <span className="demo-chip">Demo</span> : null}
          {home ? (
            <Link href="/setup/" className="btn-filled btn-small">
              <Bilingual k="getStarted" lang={uiLang} />
              <BtnArrow />
            </Link>
          ) : (
            <Link href="/settings/" className="btn-ghost btn-small">
              <Bilingual k="settings" lang={uiLang} />
            </Link>
          )}
        </div>
      </header>
      <main className={home ? "site-main site-main-home" : "site-main"}>{children}</main>
      {showBottom ? <BottomNav /> : null}
      <Footer />
    </div>
  );
}
