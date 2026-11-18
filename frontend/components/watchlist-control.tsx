"use client";

import { Check, Loader2, Plus, Star } from "lucide-react";
import { useState, useTransition } from "react";

import { addToWatchlist, createWatchlistWithMarket, removeFromWatchlist } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/format";

type Option = { id: number; name: string; contains: boolean };

export function WatchlistControl({ marketId, watchlists }: { marketId: number; watchlists: Option[] }) {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [pending, startTransition] = useTransition();
  const saved = watchlists.some((w) => w.contains);

  function act(fn: () => Promise<{ ok: boolean; error?: string }>) {
    setError(null);
    startTransition(async () => {
      const result = await fn();
      if (!result.ok) setError(result.error ?? "Something went wrong.");
      else setNewName("");
    });
  }

  return (
    <div className="relative">
      <Button variant={saved ? "secondary" : "default"} onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <Star className={cn(saved && "fill-yellow-300 text-yellow-300")} />
        {saved ? "Saved" : "Add to watchlist"}
      </Button>
      {open ? (
        <div className="absolute right-0 z-30 mt-2 w-72 rounded-xl border border-border bg-popover p-2 shadow-2xl">
          {watchlists.length ? (
            <ul className="mb-2 max-h-60 overflow-auto">
              {watchlists.map((w) => (
                <li key={w.id}>
                  <button
                    type="button"
                    disabled={pending}
                    onClick={() =>
                      act(() => (w.contains ? removeFromWatchlist(w.id, marketId) : addToWatchlist(w.id, marketId)))
                    }
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-white/[0.05] disabled:opacity-50"
                  >
                    <span
                      className={cn(
                        "grid size-4 place-items-center rounded border border-border",
                        w.contains && "border-primary bg-primary text-primary-foreground",
                      )}
                    >
                      {w.contains ? <Check className="size-3" /> : null}
                    </span>
                    <span className="line-clamp-1">{w.name}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-3 py-2 text-sm text-muted-foreground">Create your first watchlist:</p>
          )}
          <form
            className="flex gap-2 border-t border-border p-1 pt-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (newName.trim()) act(() => createWatchlistWithMarket(newName, marketId));
            }}
          >
            <Input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="New watchlist"
              maxLength={100}
              className="h-9"
            />
            <Button type="submit" size="icon" disabled={pending || !newName.trim()} aria-label="Create watchlist">
              {pending ? <Loader2 className="animate-spin" /> : <Plus />}
            </Button>
          </form>
          {error ? <p className="px-3 pt-2 text-xs text-down">{error}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
