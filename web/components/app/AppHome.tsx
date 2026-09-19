"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { BtnArrow } from "@/components/Button";
import { HistoryBar } from "@/components/app/HistoryBar";
import { LogoMark, ILLUSTRATIONS } from "@/components/marketing/illustrations";
import { SiteIntro } from "@/components/SiteIntro";
import { introAlreadySeen } from "@/lib/app/intro";
import { useApp } from "@/lib/app/store";
import { COPY, LANG_OPTIONS, scriptClass, type CopyKey, type UiLang } from "@/lib/copy";

const SLIDES: { src: string; k: CopyKey }[] = [
  { src: ILLUSTRATIONS.upload, k: "appSlide1" },
  { src: ILLUSTRATIONS.review, k: "appSlide2" },
  { src: ILLUSTRATIONS.schedule, k: "appSlide3" },
  { src: ILLUSTRATIONS.boxCheck, k: "appSlide4" },
  { src: ILLUSTRATIONS.reminder, k: "appSlide5" },
];

const LANG_CHIP: Record<UiLang, string> = {
  en: "EN",
  hi: "हिं",
  kn: "ಕ",
  te: "తె",
};

export function AppHome({ preview = false }: { preview?: boolean }) {
  const { demo, uiLang, setUiLang } = useApp();
  const firstVisit = preview ? false : !introAlreadySeen();
  const [splash, setSplash] = useState(firstVisit);
  const [slide, setSlide] = useState(0);

  useEffect(() => {
    if (preview) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const t = window.setTimeout(() => setSplash(false), reduce ? 0 : 3200);
    return () => window.clearTimeout(t);
  }, [preview]);

  useEffect(() => {
    if (splash) return;
    const t = window.setInterval(() => setSlide((n) => (n + 1) % SLIDES.length), 4200);
    return () => window.clearInterval(t);
  }, [splash]);

  const cycleLang = () => {
    const i = LANG_OPTIONS.indexOf(uiLang);
    setUiLang(LANG_OPTIONS[(i + 1) % LANG_OPTIONS.length]);
  };

  const sc = scriptClass(uiLang);

  return (
    <div className={`appv-shell${preview ? " is-preview" : ""}`}>
      {preview ? null : <SiteIntro variant="app" />}

      <div className={`appv-screen${firstVisit ? " is-in" : ""}`}>
      <header className="appv-brand-row">
        {preview ? null : <HistoryBar />}
        <span className="appv-brand-name">AfterCare</span>
        <span className="appv-spacer" />
        {!preview && demo ? <span className="demo-chip">Demo</span> : null}
        <button type="button" className="appv-icon-btn" onClick={cycleLang} aria-label={COPY.language[uiLang]}>
          {LANG_CHIP[uiLang]}
        </button>
      </header>

      <section className="appv-hero">
        <div className="appv-hero-panel">
          <div className="appv-hero-sky" aria-hidden="true">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/photos/hero-sky.png" alt="" />
          </div>
          <div className="appv-hero-still" aria-hidden="true">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/photos/hero-app-card.png" alt="" />
          </div>
          <div className="appv-hero-text">
            <h1 className={sc}>
              <span className="appv-hero-line">{COPY.appHeroLine1[uiLang]}</span>
              <span className="appv-hero-line">{COPY.appHeroLine2[uiLang]}</span>
              <span className="appv-hero-line">{COPY.appHeroLine3[uiLang]}</span>
              <span className="appv-hero-line">{COPY.appHeroLine4[uiLang]}</span>
            </h1>
            <p className={`appv-hero-sub ${sc}`}>
              <span className="appv-hero-sub-line">{COPY.appHeroSub1[uiLang]}</span>
              {COPY.appHeroSub2[uiLang] ? (
                <span className="appv-hero-sub-line">{COPY.appHeroSub2[uiLang]}</span>
              ) : null}
              {COPY.appHeroSub3[uiLang] ? (
                <span className="appv-hero-sub-line">{COPY.appHeroSub3[uiLang]}</span>
              ) : null}
            </p>
          </div>
        </div>
        <Link href="/setup/" className={`appv-hero-cta ${sc}`}>
          <CameraIcon />
          <span className="appv-hero-cta-label">{COPY.appHeroCta[uiLang]}</span>
          <BtnArrow />
        </Link>
      </section>

      <div className="appv-quick">
        <Link href="/schedule/" className="appv-card appv-tap">
          <span className="appv-ic-wrap">
            <SunIcon />
          </span>
          <h2 className={sc}>{COPY.appQuickSchedule[uiLang]}</h2>
          <p className={`appv-tiny ${sc}`}>{COPY.appQuickScheduleSub[uiLang]}</p>
        </Link>
        <Link href="/box-check/" className="appv-card appv-tap">
          <span className="appv-ic-wrap">
            <BoxIcon />
          </span>
          <h2 className={sc}>{COPY.appQuickBox[uiLang]}</h2>
          <p className={`appv-tiny ${sc}`}>{COPY.appQuickBoxSub[uiLang]}</p>
        </Link>
      </div>

      <p className={`appv-trust-kicker ${sc}`}>{COPY.appStatCaption[uiLang]}</p>
      <div className="appv-trust">
        <div className="appv-card">
          <p className="appv-trust-num">{COPY.appStatLangs[uiLang]}</p>
          <p className={`appv-trust-lbl ${sc}`}>{COPY.appStatLangsLbl[uiLang]}</p>
        </div>
        <div className="appv-card">
          <p className="appv-trust-num">{COPY.appStatVoice[uiLang]}</p>
          <p className={`appv-trust-lbl ${sc}`}>{COPY.appStatVoiceLbl[uiLang]}</p>
        </div>
        <div className="appv-card">
          <p className="appv-trust-num">{COPY.appStatPrint[uiLang]}</p>
          <p className={`appv-trust-lbl ${sc}`}>{COPY.appStatPrintLbl[uiLang]}</p>
        </div>
      </div>

      <div className="appv-carousel">
        <div className="appv-carousel-view">
          <div className="appv-carousel-track" style={{ transform: `translateX(-${slide * 100}%)` }}>
            {SLIDES.map((item) => (
              <button
                key={item.k}
                type="button"
                className="appv-carousel-slide"
                onClick={() => setSlide((n) => (n + 1) % SLIDES.length)}
                aria-label={COPY[item.k][uiLang]}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={item.src} alt="" />
                <span className={`appv-carousel-cap ${sc}`}>{COPY[item.k][uiLang]}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="appv-dots" role="tablist" aria-label={COPY.howItWorks[uiLang]}>
          {SLIDES.map((item, i) => (
            <button
              key={item.k}
              type="button"
              role="tab"
              aria-selected={i === slide}
              className={i === slide ? "is-on" : ""}
              aria-label={`${i + 1}`}
              onClick={() => setSlide(i)}
            />
          ))}
        </div>
      </div>

      <div className="appv-info">
        <Link href="/red-flags/" className="appv-card appv-tap">
          <span className="appv-ic-wrap">
            <FlagIcon />
          </span>
          <h2 className={sc}>{COPY.appInfoFlags[uiLang]}</h2>
          <p className={`appv-tiny ${sc}`}>{COPY.appInfoFlagsSub[uiLang]}</p>
        </Link>
        <Link href="/family/" className="appv-card appv-tap">
          <span className="appv-ic-wrap">
            <PeopleIcon />
          </span>
          <h2 className={sc}>{COPY.appInfoFamily[uiLang]}</h2>
          <p className={`appv-tiny ${sc}`}>{COPY.appInfoFamilySub[uiLang]}</p>
        </Link>
      </div>

      <p className={`appv-section ${sc}`}>{COPY.appSectionHome[uiLang]}</p>
      <div className="appv-info">
        <Link href="/fridge-sheet/" className="appv-card appv-tap">
          <span className="appv-ic-wrap">
            <PrintIcon />
          </span>
          <h2 className={sc}>{COPY.appHomeFridge[uiLang]}</h2>
          <p className={`appv-tiny ${sc}`}>{COPY.appHomeFridgeSub[uiLang]}</p>
        </Link>
        <Link href="/join/" className="appv-card appv-tap">
          <span className="appv-ic-wrap">
            <InviteIcon />
          </span>
          <h2 className={sc}>{COPY.appHomeInvite[uiLang]}</h2>
          <p className={`appv-tiny ${sc}`}>{COPY.appHomeInviteSub[uiLang]}</p>
        </Link>
      </div>

      <p className={`appv-section ${sc}`}>{COPY.appSectionWhy[uiLang]}</p>
      <div className="appv-card appv-why">
        <p className={sc}>
          <CheckIcon />
          {COPY.appWhy1[uiLang]}
        </p>
        <p className={sc}>
          <BlankIcon />
          {COPY.appWhy2[uiLang]}
        </p>
        <p className={sc}>
          <ShieldIcon />
          {COPY.appWhy3[uiLang]}
        </p>
      </div>

      <footer className="appv-foot">
        <div className="appv-foot-brand">
          <span className="appv-brand-mark appv-brand-mark-on-dark">
            <LogoMark className="appv-brand-svg" />
          </span>
          <span>AfterCare</span>
        </div>
        <p className={sc}>{COPY.appFooterTag[uiLang]}</p>
        <nav className="appv-foot-links" aria-label={COPY.footerStartHere[uiLang]}>
          <Link href="/setup/" className={sc}>
            {COPY.startACircle[uiLang]}
          </Link>
          <Link href="/upload/" className={sc}>
            {COPY.photographPaper[uiLang]}
          </Link>
          <Link href="/schedule/" className={sc}>
            {COPY.appQuickSchedule[uiLang]}
          </Link>
          <Link href="/box-check/" className={sc}>
            {COPY.appQuickBox[uiLang]}
          </Link>
        </nav>
        <p className={`appv-foot-legal ${sc}`}>{COPY.disclaimer[uiLang]}</p>
        <p className={`appv-foot-legal ${sc}`}>{COPY.footerLegal[uiLang]}</p>
        <p className="appv-foot-copy">© 2026 AfterCare — a demo project.</p>
      </footer>
      </div>
    </div>
  );
}

function CameraIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 8.5h3l1.4-2h7.2l1.4 2H20a1.5 1.5 0 0 1 1.5 1.5v8A1.5 1.5 0 0 1 20 19.5H4A1.5 1.5 0 0 1 2.5 18v-8A1.5 1.5 0 0 1 4 8.5Z" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="12" cy="14" r="3.2" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M12 3v2.2M12 18.8V21M3 12h2.2M18.8 12H21M5.6 5.6l1.6 1.6M16.8 16.8l1.6 1.6M18.4 5.6l-1.6 1.6M7.2 16.8 5.6 18.4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function BoxIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 8.5 12 4l8 4.5v9L12 22 4 17.5v-9Z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M12 12v10M4 8.5 12 12l8-3.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function FlagIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 4v16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M6 5h11l-2 4 2 4H6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}

function PeopleIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="9" cy="8" r="2.6" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M4.5 18c.6-3 2.4-4.5 4.5-4.5S13 15 13.6 18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="16.2" cy="9" r="2.1" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M15 13.6c2 .3 3.6 1.6 4.4 4.4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function PrintIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7 8V4.5h10V8" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M6 14.5H4.5v-6H19.5v6H18" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <rect x="7" y="12.5" width="10" height="7" rx="1.2" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function InviteIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4.5 7.5h15v11h-15z" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M4.5 7.5 12 13l7.5-5.5" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M8.5 12.2 11 14.7l4.6-5.2" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function BlankIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="5" y="5" width="14" height="14" rx="3" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 4 6 6.5v5.2c0 3.8 2.4 6.5 6 8.3 3.6-1.8 6-4.5 6-8.3V6.5L12 4Z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}
