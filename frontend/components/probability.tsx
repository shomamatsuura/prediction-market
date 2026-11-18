import { TrendingDown, TrendingUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn, pct, pts } from "@/lib/format";

export function ProbabilityBar({ value, className }: { value: number; className?: string }) {
  const width = `${Math.min(Math.max(value, 0), 1) * 100}%`;
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]", className)}>
      <div
        className="h-full rounded-full bg-gradient-to-r from-primary via-violet-400 to-cyan-300"
        style={{ width }}
      />
    </div>
  );
}

export function ProbabilityRing({ value, size = 64 }: { value: number; size?: number }) {
  const stroke = 6;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.min(Math.max(value, 0), 1);
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id="ring" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="oklch(0.72 0.17 290)" />
            <stop offset="100%" stopColor="oklch(0.82 0.12 200)" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="oklch(1 0 0 / 0.08)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="url(#ring)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${c * clamped} ${c}`}
        />
      </svg>
      <span className="absolute inset-0 grid place-items-center text-sm font-semibold tabular-nums">
        {pct(value)}
      </span>
    </div>
  );
}

export function ChangeBadge({ change, className }: { change: number; className?: string }) {
  const up = change >= 0;
  const Icon = up ? TrendingUp : TrendingDown;
  return (
    <Badge variant={up ? "up" : "down"} className={cn("tabular-nums normal-case", className)}>
      <Icon className="size-3" />
      {pts(change)}
    </Badge>
  );
}
