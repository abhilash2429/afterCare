"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useApp } from "@/lib/app/store";
import { COPY, type CopyKey } from "@/lib/copy";

const ITEMS: { href: string; k: CopyKey }[] = [
  { href: "/#how-aftercare-works", k: "howItWorks" },
  { href: "/setup/", k: "setUp" },
  { href: "/join/", k: "joinNav" },
];

export function TopNav() {
  const pathname = usePathname();
  const { uiLang } = useApp();

  return (
    <nav aria-label="Main" className="site-nav">
      {ITEMS.map((item) => {
        const active = item.href.startsWith("/#") ? false : pathname.startsWith(item.href.replace(/\/$/, ""));
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={active ? "is-active" : ""}
          >
            {COPY[item.k][uiLang]}
          </Link>
        );
      })}
    </nav>
  );
}
