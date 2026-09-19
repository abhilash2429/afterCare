import type { Metadata } from "next";
import localFont from "next/font/local";
import "@fontsource/noto-sans-kannada/kannada-400.css";
import "@fontsource/noto-sans-kannada/kannada-700.css";
import "@fontsource/noto-sans-devanagari/devanagari-400.css";
import "@fontsource/noto-sans-devanagari/devanagari-700.css";
import "@fontsource/noto-sans-telugu/telugu-400.css";
import "@fontsource/noto-sans-telugu/telugu-700.css";
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

export const metadata: Metadata = {
  title: "AfterCare",
  description:
    "Photograph an Indian hospital discharge summary. Get a picture-and-voice medicine schedule in your language.",
  icons: {
    icon: [
      { url: "/favicon.ico" },
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180" }],
  },
  appleWebApp: {
    capable: true,
    title: "AfterCare",
    statusBarStyle: "default",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const fontClassName = [funnelDisplay.variable, satishSans.variable, carmenSans.variable].join(" ");

  return (
    <html lang="en" className={fontClassName}>
      <body className="min-h-dvh antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
