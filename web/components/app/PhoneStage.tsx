"use client";

import { useRef, type ReactNode, type TouchEvent } from "react";
import { IphoneShell } from "@/components/IphoneShell";
import { VersionSwitch } from "@/components/VersionSwitch";
import { useAppHistory } from "@/lib/app/history";
import { useApp } from "@/lib/app/store";
import { useAppView } from "@/lib/app/view";
import { COPY, scriptClass } from "@/lib/copy";

export function PhoneStage({ children }: { children: ReactNode }) {
  const { uiLang } = useApp();
  const { enterWeb } = useAppView();
  const { canBack, canForward, back, forward } = useAppHistory();
  const start = useRef<{ x: number; y: number; w: number } | null>(null);

  const onTouchStart = (event: TouchEvent<HTMLDivElement>) => {
    const touch = event.changedTouches[0];
    start.current = {
      x: touch.clientX,
      y: touch.clientY,
      w: event.currentTarget.getBoundingClientRect().width,
    };
  };

  const onTouchEnd = (event: TouchEvent<HTMLDivElement>) => {
    if (!start.current) return;
    const touch = event.changedTouches[0];
    const dx = touch.clientX - start.current.x;
    const dy = Math.abs(touch.clientY - start.current.y);
    const fromLeft = start.current.x - event.currentTarget.getBoundingClientRect().left < 36;
    const fromRight = start.current.w - (start.current.x - event.currentTarget.getBoundingClientRect().left) < 36;
    start.current = null;
    if (dy > 48) return;
    if (fromLeft && dx > 48 && canBack) back();
    if (fromRight && dx < -48 && canForward) forward();
  };

  return (
    <div className="appv-stage">
      <div className="appv-phone-hit" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
        <IphoneShell className="appv-phone">{children}</IphoneShell>
      </div>
      <VersionSwitch
        href="/"
        label={COPY.seeWebVersion[uiLang]}
        className={`appv-web-fab ${scriptClass(uiLang)}`}
        onClick={enterWeb}
      />
    </div>
  );
}
