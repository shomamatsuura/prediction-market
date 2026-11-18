import Link from "next/link";

import { MarketAvatar } from "@/components/market-avatar";
import { ProbabilityBar } from "@/components/probability";
import { Badge } from "@/components/ui/badge";
import { pct, shortDate, usd } from "@/lib/format";
import type { Market } from "@/lib/types";

export function MarketCard({ market, index = 0 }: { market: Market; index?: number }) {
  return (
    <Link
      href={`/markets/${market.id}`}
      className="group glass animate-rise flex flex-col gap-4 rounded-xl border border-border p-5 transition hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-[0_8px_40px_-12px_var(--glow-a)] focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring"
      style={{ animationDelay: `${Math.min(index, 12) * 30}ms` }}
    >
      <div className="flex items-start gap-3">
        <MarketAvatar imageUrl={market.image_url} question={market.question} category={market.category} />
        <h3 className="line-clamp-2 flex-1 text-[15px] font-medium leading-snug group-hover:text-white">
          {market.question}
        </h3>
      </div>
      <div className="mt-auto space-y-2">
        <div className="flex items-baseline justify-between">
          <span className="text-2xl font-semibold tabular-nums tracking-tight">{pct(market.probability)}</span>
          <span className="text-xs text-muted-foreground">chance</span>
        </div>
        <ProbabilityBar value={market.probability} />
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <Badge>{market.category}</Badge>
        <span className="tabular-nums">
          {usd(market.volume)} vol · {shortDate(market.end_date)}
        </span>
      </div>
    </Link>
  );
}
