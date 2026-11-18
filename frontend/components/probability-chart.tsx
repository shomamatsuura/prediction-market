"use client";

import { useSyncExternalStore } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { Snapshot } from "@/lib/types";

type Point = { t: number; p: number };

const UP = "oklch(0.78 0.17 155)";
const DOWN = "oklch(0.7 0.19 18)";
const MUTED = "oklch(0.68 0.02 270)";
const HOUR = 3_600_000;
const DAY = 24 * HOUR;

/** Evenly spaced ticks on whole hours/days, so labels never repeat. */
function makeTicks(start: number, end: number, spanDays: number) {
  const step = spanDays <= 0.5 ? HOUR : spanDays <= 2 ? 4 * HOUR : Math.max(1, Math.round(spanDays / 7)) * DAY;
  const ticks: number[] = [];
  const offset = new Date(start).getTimezoneOffset() * 60_000;
  let t = Math.ceil((start - offset) / step) * step + offset;
  for (; t <= end; t += step) ticks.push(t);
  return ticks;
}

function formatTick(t: number, spanDays: number) {
  const d = new Date(t);
  return spanDays <= 2
    ? d.toLocaleTimeString("en-US", { hour: "numeric" })
    : d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

const MIN_SPAN = 10; // percentage points

/** Fit the y-axis to the data so small moves are visible, but never zoom past 10 points. */
function yAxis(values: number[]): { domain: [number, number]; ticks: number[] } {
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const pad = Math.max((hi - lo) * 0.15, 1);
  let min = Math.floor((lo - pad) / 5) * 5;
  let max = Math.ceil((hi + pad) / 5) * 5;
  while (max - min < MIN_SPAN) {
    min -= 5;
    max += 5;
  }
  if (min < 0) [min, max] = [0, Math.max(max - min, MIN_SPAN)];
  if (max > 100) [min, max] = [Math.min(min - (max - 100), 100 - MIN_SPAN), 100];
  min = Math.max(0, min);
  max = Math.min(100, max);
  // Evenly spaced ticks on round numbers (at most 6 labels).
  const step = [2, 5, 10, 20, 25].find((s) => (max - min) / s <= 5) ?? 25;
  const ticks: number[] = [];
  for (let t = Math.ceil(min / step) * step; t <= max; t += step) ticks.push(t);
  return { domain: [min, max], ticks };
}

const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

function useReducedMotion() {
  return useSyncExternalStore(
    (onChange) => {
      const mq = window.matchMedia(REDUCED_MOTION);
      mq.addEventListener("change", onChange);
      return () => mq.removeEventListener("change", onChange);
    },
    () => window.matchMedia(REDUCED_MOTION).matches,
    () => false,
  );
}

export function ProbabilityChart({ snapshots }: { snapshots: Snapshot[] }) {
  const reducedMotion = useReducedMotion();
  const data: Point[] = snapshots.map((s) => ({ t: new Date(s.captured_at).getTime(), p: s.probability * 100 }));
  if (data.length < 2) {
    return (
      <div className="grid h-72 place-items-center text-sm text-muted-foreground">
        Not enough history yet. Snapshots are recorded every hour.
      </div>
    );
  }
  const spanDays = (data[data.length - 1].t - data[0].t) / 86_400_000;
  const rising = data[data.length - 1].p >= data[0].p;
  // SVG attributes don't resolve CSS variables, so colors are literal here.
  const color = rising ? UP : DOWN;
  const ticks = makeTicks(data[0].t, data[data.length - 1].t, spanDays);
  const y = yAxis(data.map((d) => d.p));

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="prob-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="oklch(1 0 0 / 0.06)" vertical={false} />
          <XAxis
            dataKey="t"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            ticks={ticks}
            tickFormatter={(t: number) => formatTick(t, spanDays)}
            tick={{ fill: MUTED, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            minTickGap={24}
          />
          <YAxis
            domain={y.domain}
            ticks={y.ticks}
            tickFormatter={(v: number) => `${v}%`}
            tick={{ fill: MUTED, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ stroke: "oklch(1 0 0 / 0.2)" }}
            contentStyle={{
              background: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: 12,
              fontSize: 12,
            }}
            labelFormatter={(t) =>
              new Date(Number(t)).toLocaleString("en-US", {
                month: "short",
                day: "numeric",
                hour: "numeric",
                minute: "2-digit",
              })
            }
            formatter={(v) => [`${Number(v).toFixed(1)}%`, "Probability"]}
          />
          <Area
            type="monotone"
            dataKey="p"
            stroke={color}
            strokeWidth={2} fill="url(#prob-fill)"
            dot={false}
            isAnimationActive={!reducedMotion}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
