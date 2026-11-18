import Link from "next/link";

import { MarketAvatar } from "@/components/market-avatar";
import { ChangeBadge } from "@/components/probability";
import { pct } from "@/lib/format";
import type { Mover } from "@/lib/types";

export function MoverRow({ mover, rank }: { mover: Mover; rank: number }) {
  const { market } = mover;
  return (
    <Link
      href={`/markets/${market.id}`}
      className="flex items-center gap-3 rounded-lg px-3 py-2.5 transition hover:bg-white/[0.04] focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring"
    >
      <span className="w-4 text-xs tabular-nums text-muted-foreground">{rank}</span>
      <MarketAvatar imageUrl={market.image_url} question={market.question} category={market.category} size={32} />
      <span className="line-clamp-1 flex-1 text-sm">{market.question}</span>
      <span className="hidden text-xs tabular-nums text-muted-foreground sm:inline">
        {pct(mover.previous_probability)} → <span className="text-foreground">{pct(market.probability)}</span>
      </span>
      <ChangeBadge change={mover.change} />
    </Link>
  );
}
