import { SignInButton } from "@clerk/nextjs";
import { ArrowLeft, CalendarClock, Droplets, ExternalLink, Star, Wallet } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound, unstable_rethrow } from "next/navigation";

import { MarketAvatar } from "@/components/market-avatar";
import { ProbabilityChart } from "@/components/probability-chart";
import { ChangeBadge, ProbabilityRing } from "@/components/probability";
import { ApiUnavailable } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { WatchlistControl } from "@/components/watchlist-control";
import { api, isNotFound } from "@/lib/api";
import { getSessionToken } from "@/lib/auth";
import { clerkEnabled } from "@/lib/config";
import { cn, first, parseId, polymarketUrl, shortDate, usd } from "@/lib/format";

const RANGES = [
  { days: 1, label: "24H" },
  { days: 7, label: "7D" },
  { days: 30, label: "30D" },
  { days: 90, label: "90D" },
];

type Props = {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const id = parseId((await params).id);
  if (!id) return { title: "Market" };
  try {
    const market = await api.market(id);
    return { title: market.question };
  } catch {
    return { title: "Market" };
  }
}

async function WatchlistArea({ marketId }: { marketId: number }) {
  if (!clerkEnabled) return null;
  const token = await getSessionToken();
  if (!token) {
    return (
      <SignInButton mode="modal">
        <Button variant="secondary">
          <Star /> Sign in to save
        </Button>
      </SignInButton>
    );
  }
  const watchlists = await api.watchlists(token).catch(() => []);
  return (
    <WatchlistControl
      marketId={marketId}
      watchlists={watchlists.map((w) => ({
        id: w.id,
        name: w.name,
        contains: w.items.some((i) => i.market.id === marketId),
      }))}
    />
  );
}

export default async function MarketPage({ params, searchParams }: Props) {
  const id = parseId((await params).id);
  if (!id) notFound();
  const rawDays = Number(first((await searchParams).days));
  const days = RANGES.some((r) => r.days === rawDays) ? rawDays : 30;

  let market, snapshots, daySnapshots;
  try {
    [market, snapshots, daySnapshots] = await Promise.all([
      api.market(id),
      api.snapshots(id, days),
      api.snapshots(id, 1),
    ]);
  } catch (error) {
    unstable_rethrow(error);
    if (isNotFound(error)) notFound();
    console.error("Market failed to load", error);
    return <ApiUnavailable />;
  }
  const change24h = daySnapshots.length ? market.probability - daySnapshots[0].probability : 0;
  const externalUrl = polymarketUrl(market.slug);

  return (
    <div className="space-y-6">
      <Link href="/markets" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> All markets
      </Link>

      <section className="animate-rise flex flex-col gap-6 md:flex-row md:items-start">
        <MarketAvatar imageUrl={market.image_url} question={market.question} category={market.category} size={72} className="rounded-2xl" />
        <div className="flex-1 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge>{market.category}</Badge>
            {!market.active ? <Badge variant="down">Closed</Badge> : null}
          </div>
          <h1 className="text-2xl font-semibold leading-tight tracking-tight sm:text-3xl">{market.question}</h1>
          <div className="flex flex-wrap items-center gap-3">
            <WatchlistArea marketId={market.id} />
            {externalUrl ? (
              <Button asChild variant="ghost">
                <a href={externalUrl} target="_blank" rel="noopener noreferrer">
                  View on Polymarket <ExternalLink />
                </a>
              </Button>
            ) : null}
          </div>
        </div>
        <div className="glass flex items-center gap-4 rounded-2xl border border-border p-4">
          <ProbabilityRing value={market.probability} size={84} />
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Chance of “Yes”</p>
            <ChangeBadge change={change24h} />
            <p className="text-xs text-muted-foreground">vs. 24h ago</p>
          </div>
        </div>
      </section>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-base">Probability history</CardTitle>
          <div className="flex gap-1 rounded-full border border-border p-1">
            {RANGES.map((r) => (
              <Link
                key={r.days}
                href={`/markets/${market.id}?days=${r.days}`}
                scroll={false}
                className={cn(
                  "rounded-full px-3 py-1 text-xs font-medium transition",
                  r.days === days ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {r.label}
              </Link>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          <ProbabilityChart snapshots={snapshots} />
        </CardContent>
      </Card>

      <section className="grid gap-4 sm:grid-cols-3">
        {[
          { icon: Wallet, label: "Volume", value: usd(market.volume) },
          { icon: Droplets, label: "Liquidity", value: usd(market.liquidity) },
          { icon: CalendarClock, label: "Ends", value: shortDate(market.end_date) },
        ].map(({ icon: Icon, label, value }) => (
          <Card key={label} className="flex items-center gap-4 p-5">
            <span className="grid size-10 place-items-center rounded-lg bg-white/[0.05]">
              <Icon className="size-5 text-primary" />
            </span>
            <div>
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-lg font-semibold tabular-nums">{value}</p>
            </div>
          </Card>
        ))}
      </section>

      {market.description ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Resolution rules</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-line text-sm leading-relaxed text-muted-foreground">{market.description}</p>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
