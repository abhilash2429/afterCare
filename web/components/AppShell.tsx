"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Footer } from "@/components/Footer";
import { TopNav } from "@/components/TopNav";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const home = pathname === "/";

  return (
    <div className="site">
      <header className="site-header print:hidden">
        <Link href="/" className="site-logo">
          AfterCare
        </Link>
        <TopNav />
        <Link href="/upload/" className="btn-filled btn-small">
          Get started
        </Link>
      </header>
      <main className={home ? "site-main site-main-home" : "site-main"}>{children}</main>
      <Footer />
    </div>
  );
}
