"use client";

import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
};

const styles: Record<Variant, string> = {
  primary: "btn-filled",
  secondary: "btn-outline",
  ghost: "btn-ghost",
  danger: "btn-danger",
};

export function Button({ variant = "primary", className = "", children, ...props }: Props) {
  return (
    <button className={`${styles[variant]} ${className}`.trim()} {...props}>
      {children}
    </button>
  );
}

export function BtnArrow() {
  return (
    <span className="btn-arrow" aria-hidden="true">
      →
    </span>
  );
}
