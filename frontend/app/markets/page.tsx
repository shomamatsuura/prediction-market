import { Search } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { unstable_rethrow } from "next/navigation";

import { MarketCard } from "@/components/market-card";
import { ApiUnavailable, EmptyState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { cn, first } from "@/lib/format";
import type { MarketSort } from "@/lib/types";

export const metadata: Metadata = { title: "Markets" };

const PAGE_SIZE = 24;
const SORTS: { value: MarketSort; label: string }[] = [
  { value: "volume", label: "Volume" },
  { value: "liquidity", label: "Liquidity" },
  { value: "ending", label: "Ending soon" },
  { value: "probability", label: "Most likely" },
];

type Params = { q?: string; category?: string; sort: MarketSort; page: number };

/** Validate untrusted query params; anything unexpected falls back to a default. */
function parseParams(sp: Record<string, string | string[] | undefined>): Params {
  const q = first(sp.q)?.trim().slice(0, 100) || undefined;
  const rawCategory = first(sp.category);
  const category = rawCategory && /^[A-Za-z0-9 &-]{1,64}$/.test(rawCategory) ? rawCategory : undefined;
  const rawSort = first(sp.sort);
  const sort = SORTS.some((s) => s.value === rawSort) ? (rawSort as MarketSort) : "volume";
  const rawPage = Number(first(sp.page));
  const page = Number.isInteger(rawPage) && rawPage >= 1 && rawPage <= 400 ? rawPage : 1;
  return { q, category, sort, page };
}

function href(params: Params, patch: Partial<Params>) {
  const next = { ...params, ...patch };
  const qs = new URLSearchParams();
  if (next.q) qs.set("q", next.q);
  if (next.category) qs.set("category", next.category);
  if (next.sort !== "volume") qs.set("sort", next.sort);
  if (next.page > 1) qs.set("page", String(next.page));
  const s = qs.toString();
  return s ? `/markets?${s}` : "/markets";
}

function Chip({ active, href, children }: { active: boolean; href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className={cn(
        "rounded-full border px-3.5 py-1.5 text-sm capitalize transition",
        active
          ? "border-primary/40 bg-primary/15 text-foreground"
          : "border-border text-muted-foreground hover:border-white/20 hover:text-foreground",
      )}
    >
      {children}
    </Link>
  );
}

export default async function MarketsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = parseParams(await searchParams);
  let data;
  try {
    data = await Promise.all([
      api.markets({
        q: params.q,
        category: params.category,
        sort: params.sort,
        limit: PAGE_SIZE,
        offset: (params.page - 1) * PAGE_SIZE,
      }),
      api.categories(),
    ]);
  } catch (error) {
    unstable_rethrow(error);
    console.error("Markets failed to load", error);
    return <ApiUnavailable />;
  }
  const [page, categories] = data;
  const totalPages = Math.max(1, Math.ceil(page.total / PAGE_SIZE));

  return (
    <div className="space-y-8">
      <div className="animate-rise space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Markets</h1>
        <p className="text-muted-foreground">
          {page.total.toLocaleString("en-US")} active market{page.total === 1 ? "" : "s"}
          {params.category ? <> in <span className="capitalize text-foreground">{params.category}</span></> : null}
          {params.q ? <> matching “<span className="text-foreground">{params.q}</span>”</> : null}
        </p>
      </div>

      <div className="space-y-4">
        <form action="/markets" className="relative max-w-xl" role="search">
          <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input name="q" defaultValue={params.q} placeholder="Search markets…" maxLength={100} className="pl-10" />
          {params.category ? <input type="hidden" name="category" value={params.category} /> : null}
          {params.sort !== "volume" ? <input type="hidden" name="sort" value={params.sort} /> : null}
        </form>

        <div className="flex flex-wrap gap-2">
          <Chip active={!params.category} href={href(params, { category: undefined, page: 1 })}>
            All
          </Chip>
          {categories.map((c) => (
            <Chip
              key={c.category}
              active={params.category?.toLowerCase() === c.category}
              href={href(params, { category: c.category, page: 1 })}
            >
              {c.category}
            </Chip>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-1 text-sm">
          <span className="mr-2 text-muted-foreground">Sort by</span>
          {SORTS.map((s) => (
            <Link
              key={s.value}
              href={href(params, { sort: s.value, page: 1 })}
              className={cn(
                "rounded-full px-3 py-1 transition",
                params.sort === s.value ? "bg-white/[0.08] text-foreground" : "text-muted-foreground hover:text-foreground",
              )}
            >
              {s.label}
            </Link>
          ))}
        </div>
      </div>

      {page.items.length ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {page.items.map((m, i) => (
            <MarketCard key={m.id} market={m} index={i} />
          ))}
        </div>
      ) : (
        <EmptyState title="No markets found">Try a different search or category.</EmptyState>
      )}

      {totalPages > 1 ? (
        <nav className="flex items-center justify-center gap-3" aria-label="Pagination">
          <Button asChild variant="secondary" size="sm" className={cn(params.page <= 1 && "pointer-events-none opacity-40")}>
            <Link href={href(params, { page: params.page - 1 })} aria-disabled={params.page <= 1}>
              ← Previous
            </Link>
          </Button>
          <span className="text-sm tabular-nums text-muted-foreground">
            Page {params.page} of {totalPages}
          </span>
          <Button
            asChild
            variant="secondary"
            size="sm"
            className={cn(params.page >= totalPages && "pointer-events-none opacity-40")}
          >
            <Link href={href(params, { page: params.page + 1 })} aria-disabled={params.page >= totalPages}>
              Next →
            </Link>
          </Button>
        </nav>
      ) : null}
    </div>
  );
}
