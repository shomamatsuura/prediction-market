import type { Metadata } from "next";
import Link from "next/link";
import { redirect, unstable_rethrow } from "next/navigation";

import { MarketAvatar } from "@/components/market-avatar";
import { ProbabilityBar } from "@/components/probability";
import { ApiUnavailable, EmptyState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CreateWatchlistForm, DeleteWatchlistButton, RemoveItemButton } from "@/components/watchlist-forms";
import { api } from "@/lib/api";
import { getSessionToken } from "@/lib/auth";
import { clerkEnabled } from "@/lib/config";
import { pct, usd } from "@/lib/format";

export const metadata: Metadata = { title: "Watchlist" };

export default async function WatchlistPage() {
  if (!clerkEnabled) {
    return (
      <EmptyState title="Sign-in isn't configured">
        Add your Clerk keys to <code>frontend/.env.local</code> to enable watchlists.
      </EmptyState>
    );
  }
  // proxy.ts already protects this route; check again so the page never renders without a session.
  const token = await getSessionToken();
  if (!token) redirect("/sign-in");

  let watchlists;
  try {
    watchlists = await api.watchlists(token);
  } catch (error) {
    unstable_rethrow(error);
    console.error("Watchlists failed to load", error);
    return <ApiUnavailable />;
  }

  return (
    <div className="space-y-8">
      <div className="animate-rise space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Your watchlists</h1>
        <p className="text-muted-foreground">Keep an eye on the markets that matter to you.</p>
      </div>
      <CreateWatchlistForm />

      {watchlists.length === 0 ? (
        <EmptyState title="No watchlists yet">
          Create one above, or open any <Link href="/markets" className="text-primary hover:underline">market</Link>{" "}
          and add it.
        </EmptyState>
      ) : (
        <div className="space-y-6">
          {watchlists.map((w) => (
            <Card key={w.id} className="animate-rise">
              <CardHeader className="flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <CardTitle className="text-lg">{w.name}</CardTitle>
                  <Badge className="normal-case">
                    {w.items.length} market{w.items.length === 1 ? "" : "s"}
                  </Badge>
                </div>
                <DeleteWatchlistButton watchlistId={w.id} name={w.name} />
              </CardHeader>
              <CardContent className="px-3">
                {w.items.length === 0 ? (
                  <p className="px-2 py-4 text-sm text-muted-foreground">
                    Empty. Add markets from their detail page.
                  </p>
                ) : (
                  <ul className="divide-y divide-border">
                    {w.items.map(({ market }) => (
                      <li key={market.id} className="flex items-center gap-3 px-2 py-3">
                        <MarketAvatar imageUrl={market.image_url} question={market.question} category={market.category} size={36} />
                        <Link href={`/markets/${market.id}`} className="min-w-0 flex-1 space-y-1.5 hover:text-white">
                          <p className="line-clamp-1 text-sm font-medium">{market.question}</p>
                          <ProbabilityBar value={market.probability} className="max-w-xs" />
                        </Link>
                        <span className="hidden w-20 text-right text-xs tabular-nums text-muted-foreground sm:block">
                          {usd(market.volume)}
                        </span>
                        <span className="w-14 text-right font-semibold tabular-nums">{pct(market.probability)}</span>
                        <RemoveItemButton watchlistId={w.id} marketId={market.id} />
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
