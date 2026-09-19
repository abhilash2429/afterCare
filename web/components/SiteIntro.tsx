"use client";

import { useEffect, useState } from "react";
import { introAlreadySeen, markIntroSeen } from "@/lib/app/intro";

const MARK = "AfterCare".split("");

export function SiteIntro({
  variant = "web",
}: {
  variant?: "web" | "app";
}) {
  const [phase, setPhase] = useState<"in" | "out" | "off">(introAlreadySeen() ? "off" : "in");

  useEffect(() => {
    if (introAlreadySeen()) {
      setPhase("off");
      return;
    }
    markIntroSeen();
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setPhase("off");
      return;
    }
    const out = window.setTimeout(() => setPhase("out"), 2300);
    const off = window.setTimeout(() => {
      setPhase("off");
    }, 3200);
    return () => {
      window.clearTimeout(out);
      window.clearTimeout(off);
    };
  }, []);

  if (phase === "off") return null;

  return (
    <div className={`site-intro site-intro-${variant}${phase === "out" ? " is-out" : ""}`} aria-hidden="true">
      <p className="site-intro-word">
        {MARK.map((letter, i) => (
          <span
            key={`${letter}${i}`}
            style={{ animationDelay: `${i * 50}ms, ${880 + i * 80}ms` }}
          >
            {letter}
          </span>
        ))}
      </p>
    </div>
  );
}
