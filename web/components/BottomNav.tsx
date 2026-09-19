"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bilingual } from "@/components/Bilingual";
import { useApp } from "@/lib/app/store";
import { useAppView } from "@/lib/app/view";
import type { CopyKey } from "@/lib/copy";

const ITEMS: { href: string; k: CopyKey; match: string }[] = [
  { href: "/schedule/", k: "schedule", match: "/schedule" },
  { href: "/box-check/", k: "boxCheck", match: "/box-check" },
  { href: "/red-flags/", k: "redFlags", match: "/red-flags" },
];

const APP_HOME: { href: string; k: CopyKey; match: string } = {
  href: "/app/",
  k: "appMenuHome",
  match: "/app",
};

export function BottomNav() {
  const pathname = usePathname();
  const { uiLang } = useApp();
  const { isApp } = useAppView();
  const items = isApp ? [APP_HOME, ...ITEMS] : ITEMS;

  return (
    <nav aria-label="Care" className="bottom-nav print:hidden">
      {items.map((item) => {
        const active = pathname.startsWith(item.match);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={active ? "is-active" : ""}
          >
            <Bilingual k={item.k} lang={uiLang} stacked />
          </Link>
        );
      })}
    </nav>
  );
}
