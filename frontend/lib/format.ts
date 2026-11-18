import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function pct(p: number, digits = 0) {
  const value = p * 100;
  if (value > 0 && value < 1 && digits === 0) return "<1%";
  if (value < 100 && value > 99 && digits === 0) return ">99%";
  return `${value.toFixed(digits)}%`;
}

/** Signed change in percentage points, e.g. "+4.2 pts". */
export function pts(change: number) {
  const value = change * 100;
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${Math.abs(value).toFixed(1)} pts`;
}

const compact = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});

export function usd(n: number) {
  return compact.format(n);
}

export function shortDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

/** Parse a positive integer route/query param; returns null for anything else. */
export function parseId(value: string | string[] | undefined): number | null {
  if (typeof value !== "string" || !/^[1-9]\d{0,9}$/.test(value)) return null;
  return Number(value);
}

export function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export function polymarketUrl(slug: string | null) {
  if (!slug || !/^[a-z0-9-]+$/i.test(slug)) return null;
  return `https://polymarket.com/market/${slug}`;
}
