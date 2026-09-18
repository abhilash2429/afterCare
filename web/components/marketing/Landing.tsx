"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { ILLUSTRATIONS, PhoneMockup, ScenePhoto } from "@/components/marketing/illustrations";

export const PHOTOS = {
  hero: "/photos/hero-care.png",
};

const STORY = [
  {
    id: "story-paper",
    n: "01",
    path: "Photograph",
    title: "Photograph the paper",
    body: "The discharge summary is the source. Hold it up to the phone. AfterCare copies each line the doctor wrote. If a strength or number is missing, that space stays empty. We do not guess.",
    src: ILLUSTRATIONS.upload,
    href: "/upload/",
    cta: "Photograph a page",
  },
  {
    id: "story-day",
    n: "02",
    path: "See the day",
    title: "See it as a day",
    body: "The same medicines, grouped into morning, noon, night, and bedtime. A son or daughter looks it over once. Then the household can follow the day — still in the doctor’s words.",
    src: ILLUSTRATIONS.review,
    href: "/review/",
    cta: "Look at a schedule",
  },
  {
    id: "story-voice",
    n: "03",
    path: "Hear the dose",
    title: "Hear the next dose",
    body: "When it is time, the phone speaks the tablet in your language. Tap Given. You do not have to read small print at eight in the evening.",
    src: ILLUSTRATIONS.schedule,
    href: "/schedule/",
    cta: "Open the schedule",
  },
  {
    id: "story-box",
    n: "04",
    path: "Check the box",
    title: "Check the strips you bought",
    body: "Photograph the blister in your hand. AfterCare says if it matches the paper, if it needs a second look, or if it should not be taken. It never says a strip is safe.",
    src: ILLUSTRATIONS.boxCheck,
    href: "/box-check/",
    cta: "Check the box",
  },
  {
    id: "story-home",
    n: "05",
    path: "Stay at home",
    title: "Keep going at home",
    body: "Reminders land on the phone. Print a sheet for the fridge. A daughter or son can watch along. They cannot change the plan.",
    src: ILLUSTRATIONS.reminder,
    href: "/fridge-sheet/",
    cta: "Open the fridge sheet",
  },
] as const;

export function Landing() {
  return (
    <div className="landing">
      <section className="landing-hero">
        <h1>
          <span className="hero-phrase">
            Photograph the <HeroMark variant="paper">paper</HeroMark>.
          </span>{" "}
          Check the <HeroMark variant="pill">pill box</HeroMark>.
        </h1>
        <p className="landing-lead">
          AfterCare re-displays what the doctor wrote. It never changes a dose.
        </p>
        <div className="landing-hero-actions">
          <Link href="/upload/" className="btn-filled">
            Photograph the paper
          </Link>
          <Link href="/box-check/" className="btn-outline">
            Check the box
          </Link>
        </div>
      </section>

      <section className="landing-hero-visual">
        <div className="landing-photo">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={PHOTOS.hero} alt="Daughter and mother checking the discharge summary and pill box together" />
          <article className="landing-float landing-float-a">
            <p className="landing-float-kicker">Morning · 08:00</p>
            <p>Ecosprin, Pan, Glycomet GP1</p>
          </article>
          <article className="landing-float landing-float-c">
            <p className="landing-float-kicker">From your document</p>
            <p>Report chest pain, breathlessness or bleeding.</p>
          </article>
          <div className="landing-phone">
            <article className="landing-float landing-float-b">
              <p className="landing-float-kicker">Box Check</p>
              <p>This matches your prescription.</p>
            </article>
            <PhoneMockup />
          </div>
        </div>
      </section>

      <section className="story" id="how-aftercare-works">
        <Reveal className="story-intro">
          <p className="landing-eyebrow">How AfterCare works</p>
          <h2>
            The hospital paper
            <br />
            stays in charge.
          </h2>
          <p className="story-lead">
            After you leave the hospital, the discharge page is easy to lose in a stack of strips
            and bottles. Photograph that page. AfterCare shows the same words as a daily schedule,
            speaks the next dose, and checks the box you bought. It never changes a dose.
          </p>
        </Reveal>

        <StoryFlow />

        <Reveal className="story-guard">
          <p className="landing-eyebrow" id="promises">What we will not do</p>
          <h2>Three promises you can hold us to.</h2>
          <div className="story-guard-grid">
            <article>
              <p className="story-guard-title">Never change a dose</p>
              <p>The tablet, the time, and the food instruction stay as the doctor wrote them.</p>
            </article>
            <article>
              <p className="story-guard-title">Never fill a blank</p>
              <p>If the paper is missing a strength or a number of days, we leave that space empty.</p>
            </article>
            <article>
              <p className="story-guard-title">Never say “safe to take”</p>
              <p>Box Check can match, ask you to look again, or say do not take. That is all.</p>
            </article>
          </div>
        </Reveal>

        <Reveal className="story-close">
          <h2>Start with the paper in your hand.</h2>
          <div className="landing-hero-actions">
            <Link href="/upload/" className="btn-filled">
              Photograph the paper
            </Link>
            <Link href="/join/" className="btn-outline">
              Join a family circle
            </Link>
          </div>
        </Reveal>
      </section>
    </div>
  );
}

const HERO_SCRIBBLES = {
  paper:
    "M4 11.8 C60 3.2 122 2.2 180 4.1 C206 4.9 234 6.1 258 7.2 C274 8 304 9.6 286 12.4 C274 13.6 258 13.2 242 13.6 C208 14.6 172 15.8 136 17.2 C100 18.6 66 20.2 40 19.6 C26 19.2 14 19.6 12 17.8 C10 15.8 24 13.2 38 12.4 C62 10.4 90 9.6 118 8.6 C156 7.2 194 5.6 230 3.8 C248 2.8 270 1.2 284 1.6",
  pill:
    "M3 12.2 C64 3.6 130 2.4 186 4.2 C212 5 238 6.2 260 7.4 C276 8.3 304 9.8 288 12.8 C276 14 260 13.6 244 14 C210 15 174 16.2 138 17.4 C102 18.6 68 20.4 42 19.4 C28 18.9 16 19.4 14 17.6 C12 15.6 26 13.6 40 12.8 C66 10.8 96 10 124 9 C162 7.6 200 5.8 236 3.8 C254 2.8 274 1.1 286 1.5",
} as const;

function HeroMark({
  children,
  variant,
}: {
  children: ReactNode;
  variant: "paper" | "pill";
}) {
  return (
    <span className="hero-mark">
      {children}
      <svg
        className={`hero-scribble hero-scribble-${variant}`}
        viewBox="0 0 310 21"
        aria-hidden="true"
        preserveAspectRatio="xMidYMid meet"
      >
        <path pathLength="100" d={HERO_SCRIBBLES[variant]} />
      </svg>
    </span>
  );
}

function StoryFlow() {
  const [active, setActive] = useState(0);
  const [fill, setFill] = useState(0);

  useEffect(() => {
    const update = () => {
      const nodes = STORY.map((beat) => document.getElementById(beat.id));
      if (nodes.some((node) => !node)) return;
      const marker = window.innerHeight * 0.4;
      const tops = nodes.map((node) => node!.getBoundingClientRect().top);
      const span = tops[tops.length - 1] - tops[0];
      const progress =
        span <= 0 ? 0 : Math.min(1, Math.max(0, (marker - tops[0]) / span));
      let next = 0;
      tops.forEach((top, index) => {
        if (top <= marker + 28) next = index;
      });
      setActive(next);
      setFill(progress * 100);
    };

    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    window.addEventListener("hashchange", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
      window.removeEventListener("hashchange", update);
    };
  }, []);

  return (
    <div className="story-flow">
      <nav className="story-rail" aria-label="How AfterCare works">
        <div className="story-rail-track" aria-hidden="true">
          <div className="story-rail-fill" style={{ height: `${fill}%` }} />
        </div>
        <ol>
          {STORY.map((beat, index) => {
            const state =
              index < active ? "is-done" : index === active ? "is-active" : "";
            return (
              <li key={beat.id}>
                <a href={`#${beat.id}`} className={state}>
                  <span>{beat.n}</span>
                  {beat.path}
                </a>
              </li>
            );
          })}
        </ol>
      </nav>

      <div className="story-beats">
        {STORY.map((beat, index) => (
          <Reveal key={beat.id} className="story-beat" delay={index * 40}>
            <article id={beat.id}>
              <div className="story-art">
                <ScenePhoto src={beat.src} className="story-illu" />
              </div>
              <div className="story-copy">
                <h3>{beat.title}</h3>
                <p className="story-body">{beat.body}</p>
                <Link href={beat.href} className="btn-outline btn-small">
                  {beat.cta} →
                </Link>
              </div>
            </article>
          </Reveal>
        ))}
      </div>
    </div>
  );
}

function Reveal({
  children,
  className = "",
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [on, setOn] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const reveal = () => setOn(true);
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) reveal();
      },
      { threshold: 0.08, rootMargin: "80px 0px -10% 0px" },
    );
    observer.observe(node);
    const rect = node.getBoundingClientRect();
    if (rect.top < window.innerHeight * 0.92 && rect.bottom > 72) reveal();
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`landing-reveal ${on ? "is-in" : ""} ${className}`}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </div>
  );
}
