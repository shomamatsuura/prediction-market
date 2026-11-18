import { Show, SignInButton, UserButton } from "@clerk/nextjs";
import { Activity } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { clerkEnabled } from "@/lib/config";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/markets", label: "Markets" },
  { href: "/watchlist", label: "Watchlist" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/60 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="grid size-8 place-items-center rounded-lg bg-gradient-to-br from-primary to-cyan-400 text-primary-foreground shadow-[0_0_24px_-4px_var(--primary)]">
            <Activity className="size-4" strokeWidth={2.5} />
          </span>
          <span className="hidden sm:inline">Oddsboard</span>
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-full px-3 py-1.5 text-muted-foreground transition hover:bg-white/[0.05] hover:text-foreground"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          {clerkEnabled ? (
            <>
              <Show when="signed-out">
                <SignInButton mode="modal">
                  <Button size="sm">Sign in</Button>
                </SignInButton>
              </Show>
              <Show when="signed-in">
                <UserButton />
              </Show>
            </>
          ) : null}
        </div>
      </div>
    </header>
  );
}
