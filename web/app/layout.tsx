import type { Metadata } from "next";
import localFont from "next/font/local";
import { Noto_Sans_Devanagari, Noto_Sans_Kannada } from "next/font/google";
import { Providers } from "@/app/providers";
import "./globals.css";

const funnelDisplay = localFont({
  src: [
    { path: "./fonts/FunnelDisplay-Regular.ttf", weight: "400", style: "normal" },
    { path: "./fonts/FunnelDisplay-Bold.ttf", weight: "700", style: "normal" },
  ],
  variable: "--font-funnel",
  display: "swap",
});

const satishSans = localFont({
  src: "./fonts/Satish-sans.ttf",
  variable: "--font-satish",
  display: "swap",
  weight: "400",
});

const carmenSans = localFont({
  src: "./fonts/CarmenSans-Bold.ttf",
  variable: "--font-carmen",
  display: "swap",
  weight: "700",
});

const notoKannada = Noto_Sans_Kannada({
  subsets: ["kannada"],
  weight: ["400", "600", "700"],
  variable: "--font-kannada",
  display: "swap",
});

const notoDevanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari"],
  weight: ["400", "600", "700"],
  variable: "--font-devanagari",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AfterCare",
  description:
    "Photograph an Indian hospital discharge summary. Get a picture-and-voice medicine schedule in your language.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    title: "AfterCare",
    statusBarStyle: "default",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const fontClassName = [
    funnelDisplay.variable,
    satishSans.variable,
    carmenSans.variable,
    notoKannada.variable,
    notoDevanagari.variable,
  ].join(" ");

  return (
    <html lang="en" className={fontClassName}>
      <body className="min-h-dvh antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
