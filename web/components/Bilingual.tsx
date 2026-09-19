"use client";

import { COPY, isCopyKey, scriptClass, type CopyKey, type UiLang } from "@/lib/copy";

export function Bilingual({
  k,
  lang,
  className = "",
}: {
  k: CopyKey;
  lang: UiLang;
  className?: string;
  stacked?: boolean;
}) {
  return <span className={`${className} ${scriptClass(lang)}`.trim()}>{COPY[k][lang]}</span>;
}

export function Regional({
  text,
  lang,
  className = "muted",
}: {
  text: string;
  lang: UiLang;
  className?: string;
}) {
  if (!text) return null;
  return <p className={`${scriptClass(lang)} ${className}`.trim()}>{text}</p>;
}

export function CopyLine({
  k,
  lang,
  as: Tag = "p",
  className = "",
}: {
  k: CopyKey | string;
  lang: UiLang;
  as?: "span" | "p" | "h1" | "h2" | "legend";
  className?: string;
  regionalClassName?: string;
}) {
  const text = isCopyKey(k) ? COPY[k][lang] : k;
  return <Tag className={`${className} ${scriptClass(lang)}`.trim()}>{text}</Tag>;
}
