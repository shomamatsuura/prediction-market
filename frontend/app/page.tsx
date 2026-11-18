import { ArrowRight, Flame, TrendingDown, TrendingUp } from "lucide-react";
import Link from "next/link";
import { unstable_rethrow } from "next/navigation";

import { MarketCard } from "@/components/market-card";
import { MoverRow } from "@/components/mover-row";
import { ApiUnavailable, EmptyState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { pts } from "@/lib/format";
import type { Mover } from "@/lib/types";

async function loadDashboard() {
  try {
    const [gainers, decliners, trending, categories, all] = await Promise.all([
      api.movers({ hours: 24, limit: 6, direction: "up" }),
      api.movers({ hours: 24, limit: 6, direction: "down" }),
      api.markets({ sort: "volume", limit: 6 }),
      api.categories(),
      api.movers({ hours: 24, limit: 1 }),
    ]);
    return { gainers, decliners, trending, categories, biggest: all[0] as Mover | undefined };
  } catch (error) {
    unstable_rethrow(error);
    console.error("Dashboard data failed to load", error);
    return null;
  }
}

function MoversCard({ title, icon, movers }: { title: string; icon: React.ReactNode; movers: Mover[] }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center gap-2">
        {icon}
        <CardTitle className="text-base">{title}</CardTitle>
        <span className="ml-auto text-xs text-muted-foreground">last 24h</span>
      </CardHeader>
      <CardContent className="px-2 pb-3">
        {movers.length ? (
          movers.map((m, i) => <MoverRow key={m.market.id} mover={m} rank={i + 1} />)
        ) : (
          <p className="px-3 py-6 text-sm text-muted-foreground">No moves yet. Check back after a few hourly runs.</p>
        )}
      </CardContent>
    </Card>
  );
}

export default async function DashboardPage() {
  const data = await loadDashboard();
  if (!data) return <ApiUnavailable />;
  const { gainers, decliners, trending, categories, biggest } = data;
  const tracked = categories.reduce((sum, c) => sum + c.count, 0);

  return (
    <div className="space-y-12">
      <section className="animate-rise space-y-6">
        <Badge variant="primary" className="normal-case">
          <span className="size-1.5 animate-pulse rounded-full bg-primary" /> Live · refreshed hourly
        </Badge>
        <h1 className="max-w-3xl text-4xl font-semibold tracking-tight sm:text-6xl">
          <span className="text-gradient">Prediction markets,</span>
          <br />
          in motion.
        </h1>
        <p className="max-w-xl text-muted-foreground sm:text-lg">
          Follow how the crowd&apos;s odds shift on politics, crypto, sports and more. Spot the biggest swings and keep
          a watchlist of the markets you care about.
        </p>
        <div className="flex flex-wrap gap-3">
          <Button asChild size="lg">
            <Link href="/markets">
              Explore markets <ArrowRight />
            </Link>
          </Button>
          <Button asChild size="lg" variant="secondary">
            <Link href="/watchlist">My watchlist</Link>
          </Button>
        </div>
        <dl className="grid max-w-2xl grid-cols-3 gap-3 pt-2">
          {[
            { label: "Markets tracked", value: tracked.toLocaleString("en-US") },
            { label: "Categories", value: categories.length },
            { label: "Biggest 24h swing", value: biggest ? pts(biggest.change) : "—" },
          ].map((stat) => (
            <div key={stat.label} className="glass rounded-xl border border-border px-4 py-3">
              <dt className="text-xs text-muted-foreground">{stat.label}</dt>
              <dd className="mt-1 text-xl font-semibold tabular-nums">{stat.value}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <MoversCard title="Top gainers" icon={<TrendingUp className="size-4 text-up" />} movers={gainers} />
        <MoversCard title="Top decliners" icon={<TrendingDown className="size-4 text-down" />} movers={decliners} />
      </section>

      <section className="space-y-4">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
              <Flame className="size-5 text-orange-400" /> Trending by volume
            </h2>
            <CardDescription>Where the most money is being traded.</CardDescription>
          </div>
          <Link href="/markets" className="text-sm text-muted-foreground hover:text-foreground">
            View all →
          </Link>
        </div>
        {trending.items.length ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {trending.items.map((m, i) => (
              <MarketCard key={m.id} market={m} index={i} />
            ))}
          </div>
        ) : (
          <EmptyState title="No markets yet">The first ingestion run will fill this in.</EmptyState>
        )}
      </section>

      {categories.length ? (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold tracking-tight">Browse by category</h2>
          <div className="flex flex-wrap gap-2">
            {categories.map((c) => (
              <Link
                key={c.category}
                href={`/markets?category=${encodeURIComponent(c.category)}`}
                className="glass rounded-full border border-border px-4 py-2 text-sm capitalize transition hover:border-primary/40"
              >
                {c.category} <span className="ml-1 text-muted-foreground tabular-nums">{c.count}</span>
              </Link>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
