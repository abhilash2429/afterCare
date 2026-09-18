"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/upload/", label: "Upload", match: (path: string) => path.startsWith("/upload") },
  { href: "/review/", label: "Review", match: (path: string) => path.startsWith("/review") },
  { href: "/schedule/", label: "Schedule", match: (path: string) => path.startsWith("/schedule") },
  { href: "/box-check/", label: "Box Check", match: (path: string) => path.startsWith("/box-check") },
  { href: "/red-flags/", label: "Red flags", match: (path: string) => path.startsWith("/red-flags") },
];

export function TopNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Main" className="site-nav">
      {ITEMS.map((item) => {
        const active = item.match(pathname);
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={active ? "is-active" : ""}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
