"use client";

import { Loader2, Plus, Trash2, X } from "lucide-react";
import { useActionState, useState, useTransition } from "react";

import { createWatchlist, deleteWatchlist, removeFromWatchlist, type ActionResult } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function CreateWatchlistForm() {
  const [state, formAction, pending] = useActionState<ActionResult | null, FormData>(createWatchlist, null);
  return (
    <form action={formAction} className="flex max-w-md flex-col gap-2">
      <div className="flex gap-2">
        <Input name="name" placeholder="Name a new watchlist" maxLength={100} required />
        <Button type="submit" disabled={pending}>
          {pending ? <Loader2 className="animate-spin" /> : <Plus />} Create
        </Button>
      </div>
      {state && !state.ok ? <p className="text-xs text-down">{state.error}</p> : null}
    </form>
  );
}

export function RemoveItemButton({ watchlistId, marketId }: { watchlistId: number; marketId: number }) {
  const [pending, startTransition] = useTransition();
  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label="Remove from watchlist"
      disabled={pending}
      onClick={() => startTransition(async () => void (await removeFromWatchlist(watchlistId, marketId)))}
    >
      {pending ? <Loader2 className="animate-spin" /> : <X />}
    </Button>
  );
}

export function DeleteWatchlistButton({ watchlistId, name }: { watchlistId: number; name: string }) {
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  return (
    <div className="flex items-center gap-2">
      {error ? <span className="text-xs text-down">{error}</span> : null}
      <Button
        variant="destructive"
        size="sm"
        disabled={pending}
        onClick={() => {
          if (!window.confirm(`Delete the watchlist “${name}”? This can't be undone.`)) return;
          startTransition(async () => {
            const result = await deleteWatchlist(watchlistId);
            if (!result.ok) setError(result.error);
          });
        }}
      >
        {pending ? <Loader2 className="animate-spin" /> : <Trash2 />} Delete
      </Button>
    </div>
  );
}
