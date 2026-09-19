import type { ReactNode } from "react";
import { IphoneShell } from "@/components/IphoneShell";

const BLUE = "#0061FE";
const PAPER = "#FFFFFF";

export const ILLUSTRATIONS = {
  upload: "/illustrations/upload-discharge.png",
  review: "/illustrations/laptop-schedule.png",
  schedule: "/illustrations/voice-schedule.png",
  boxCheck: "/illustrations/box-check.png",
  reminder: "/illustrations/chair-reminder.png",
} as const;

export function ScenePhoto({
  src,
  className = "",
}: {
  src: string;
  className?: string;
}) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt="" className={`scene-photo ${className}`.trim()} aria-hidden="true" />
  );
}

export function LogoMark({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <circle cx="16" cy="16" r="15" fill={BLUE} />
      <rect x="10" y="8" width="12" height="15" rx="2" fill={PAPER} />
      <rect x="12" y="18" width="8" height="3.5" rx="1.75" fill={BLUE} />
    </svg>
  );
}

export function PhoneMockup({
  children,
  className = "",
}: {
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`phone-mock ${className}`.trim()} aria-hidden="true">
      <IphoneShell>
        <div className="phone-mock-app" inert>
          {children}
        </div>
      </IphoneShell>
    </div>
  );
}
