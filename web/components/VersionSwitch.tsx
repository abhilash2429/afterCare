"use client";

import type { MouseEvent } from "react";
import { BtnArrow } from "@/components/Button";
import { resetIntro } from "@/lib/app/intro";

export function VersionSwitch({
  href,
  label,
  className = "",
  onClick,
}: {
  href: string;
  label: string;
  className?: string;
  onClick?: () => void;
}) {
  const go = (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      onClick?.();
      return;
    }
    event.preventDefault();
    resetIntro();
    onClick?.();
    window.location.href = href;
  };

  return (
    <a href={href} className={`version-switch ${className}`.trim()} onClick={go}>
      {label}
      <BtnArrow />
    </a>
  );
}
