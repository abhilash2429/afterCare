import Link from "next/link";
import { Disclaimer } from "@/components/Disclaimer";

const COLUMNS = [
  {
    title: "Start here",
    links: [
      { href: "/upload/", label: "Photograph the paper" },
      { href: "/review/", label: "Review the extraction" },
      { href: "/schedule/", label: "See the day" },
    ],
  },
  {
    title: "At home",
    links: [
      { href: "/box-check/", label: "Check the box" },
      { href: "/fridge-sheet/", label: "Fridge sheet" },
      { href: "/join/", label: "Join a family circle" },
    ],
  },
  {
    title: "Guide",
    links: [
      { href: "/#how-aftercare-works", label: "How AfterCare works" },
      { href: "/red-flags/", label: "Red flags" },
      { href: "/#promises", label: "What we will not do" },
      { href: "/settings/", label: "Settings" },
    ],
  },
] as const;

const SOCIAL = [
  { label: "Instagram", icon: InstagramIcon },
  { label: "X", icon: XIcon },
  { label: "Facebook", icon: FacebookIcon },
  { label: "YouTube", icon: YouTubeIcon },
  { label: "WhatsApp", icon: WhatsAppIcon },
] as const;

export function Footer() {
  return (
    <footer className="site-footer print:hidden">
      <div className="site-footer-inner">
        <div className="site-footer-brand">
          <Link href="/" className="site-footer-logo">
            AfterCare
          </Link>
          <p className="site-footer-tagline">
            Photograph the paper. Check the pill box.
          </p>
          <div className="site-footer-social" aria-hidden="true">
            {SOCIAL.map((item) => (
              <span key={item.label}>
                <item.icon />
              </span>
            ))}
          </div>
          <p className="site-footer-copy">© 2026 AfterCare — a demo project.</p>
        </div>

        <div className="site-footer-navs">
          {COLUMNS.map((column) => (
            <nav key={column.title} className="site-footer-col" aria-label={column.title}>
              <h2>{column.title}</h2>
              <ul>
                {column.links.map((link) => (
                  <li key={link.href}>
                    <Link href={link.href}>{link.label}</Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>
      </div>

      <div className="site-footer-legal">
        <Disclaimer />
        <p>
          AfterCare is not a hospital, pharmacy, or official government service. It is an
          independent prototype. For medical advice, contact your doctor or nearest hospital
          directly.
        </p>
      </div>
    </footer>
  );
}

function InstagramIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3.5" y="3.5" width="17" height="17" rx="5" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="17.2" cy="6.8" r="1" fill="currentColor" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M5 5.5 10.8 12 5.2 18.5h2.2L12 13.4l4.5 5.1h2.3L12.8 11.8 18.2 5.5h-2.2L12 10.4 7.3 5.5H5Z"
        fill="currentColor"
      />
    </svg>
  );
}

function FacebookIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M14.2 20v-7.1h2.4l.4-2.8h-2.8V8.4c0-.8.2-1.4 1.4-1.4h1.5V4.5c-.3 0-1.2-.1-2.3-.1-2.3 0-3.8 1.4-3.8 3.9v2.2H8.6v2.8h2.4V20h3.2Z"
        fill="currentColor"
      />
    </svg>
  );
}

function YouTubeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3" y="7" width="18" height="10" rx="3" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M11 10.2 15 12l-4 1.8v-3.6Z" fill="currentColor" />
    </svg>
  );
}

function WhatsAppIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M7.4 18.6 6 20.8l.6-2.3A7.8 7.8 0 1 1 18.7 12a7.8 7.8 0 0 1-11.3 6.6Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      />
      <path
        d="M9.2 8.8c.2-.4.4-.5.8-.5h.6c.2 0 .4.1.5.4l.6 1.4c.1.2 0 .5-.2.6l-.5.4c-.1.1-.1.3 0 .5.4.7 1.1 1.4 1.9 1.8.2.1.4.1.5 0l.5-.4c.2-.2.5-.2.6 0l1.2.8c.2.2.3.4.2.6l-.2.6c-.1.3-.3.5-.6.6-.3.1-.8.2-1.6 0-1.7-.5-3.2-1.7-4.2-3.3-.9-1.3-1.1-2.5-1-3.1.1-.3.3-.5.5-.6Z"
        fill="currentColor"
      />
    </svg>
  );
}
