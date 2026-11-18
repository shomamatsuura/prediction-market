import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { connection } from "next/server";

import { SiteHeader } from "@/components/site-header";
import { clerkEnabled } from "@/lib/config";

import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Oddsboard · Prediction market analytics", template: "%s · Oddsboard" },
  description: "Track how prediction market probabilities move over time.",
};

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  // Render every page per request: the CSP nonce from proxy.ts only exists at request time.
  await connection();
  const body = (
    <html lang="en" className="dark">
      <body className={`${geistSans.variable} ${geistMono.variable} min-h-dvh font-sans`}>
        <div className="app-backdrop" aria-hidden />
        <SiteHeader />
        <main className="mx-auto max-w-6xl px-4 pb-24 pt-10 sm:px-6">{children}</main>
        <footer className="mx-auto max-w-6xl px-4 pb-10 text-xs text-muted-foreground sm:px-6">
          Data from Polymarket&apos;s public API, refreshed hourly. Not affiliated with Polymarket.
        </footer>
      </body>
    </html>
  );
  // `dynamic` makes Clerk read the per-request CSP nonce for its scripts.
  return clerkEnabled ? (
    <ClerkProvider dynamic appearance={{ variables: { colorPrimary: "oklch(0.72 0.17 290)" } }}>
      {body}
    </ClerkProvider>
  ) : (
    body
  );
}
