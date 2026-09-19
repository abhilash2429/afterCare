"use client";

import type { ReactNode } from "react";

export function IphoneShell({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`iphone-shell ${className}`.trim()}>
      <span className="iphone-hw iphone-hw-silent" />
      <span className="iphone-hw iphone-hw-vol-up" />
      <span className="iphone-hw iphone-hw-vol-down" />
      <span className="iphone-hw iphone-hw-power" />
      <div className="iphone-bezel">
        <div className="iphone-island" aria-hidden="true">
          <span className="iphone-island-lens" />
        </div>
        <div className="iphone-status" aria-hidden="true">
          <span className="iphone-time">9:41</span>
          <span className="iphone-status-right">
            <CellularIcon />
            <WifiIcon />
            <BatteryIcon />
          </span>
        </div>
        <div className="iphone-screen">{children}</div>
      </div>
    </div>
  );
}

function CellularIcon() {
  return (
    <svg viewBox="0 0 18 12" aria-hidden="true">
      <rect x="0" y="8" width="3" height="4" rx="0.6" fill="currentColor" />
      <rect x="5" y="5.5" width="3" height="6.5" rx="0.6" fill="currentColor" />
      <rect x="10" y="3" width="3" height="9" rx="0.6" fill="currentColor" />
      <rect x="15" y="0.5" width="3" height="11.5" rx="0.6" fill="currentColor" />
    </svg>
  );
}

function WifiIcon() {
  return (
    <svg viewBox="0 0 16 12" aria-hidden="true">
      <path
        d="M8 10.6a1.15 1.15 0 1 0 0-2.3 1.15 1.15 0 0 0 0 2.3Zm-3.3-2.4a4.7 4.7 0 0 1 6.6 0l-1.1 1.1a3.1 3.1 0 0 0-4.4 0L4.7 8.2Zm-2.5-2.4a8.2 8.2 0 0 1 11.6 0L12.7 7a6.6 6.6 0 0 0-9.4 0L2.2 5.8Z"
        fill="currentColor"
      />
    </svg>
  );
}

function BatteryIcon() {
  return (
    <svg viewBox="0 0 27 12" aria-hidden="true">
      <rect x="0.6" y="1.2" width="22.5" height="9.6" rx="2.2" fill="none" stroke="currentColor" strokeWidth="1.2" />
      <rect x="2.3" y="2.9" width="18" height="6.2" rx="1.1" fill="currentColor" />
      <path d="M24.4 4.1h.8c.9 0 1.4.6 1.4 1.4v1c0 .8-.5 1.4-1.4 1.4h-.8V4.1Z" fill="currentColor" opacity="0.45" />
    </svg>
  );
}
