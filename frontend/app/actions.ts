"use server";

import { revalidatePath } from "next/cache";

import { api, ApiError } from "@/lib/api";
import { getSessionToken } from "@/lib/auth";

/**
 * Server Actions are public HTTP endpoints, so every input is validated here, and the
 * backend independently checks the session token and watchlist ownership.
 */

export type ActionResult = { ok: true } | { ok: false; error: string };

function toId(value: unknown): number | null {
  const n = typeof value === "string" ? Number(value) : value;
  return typeof n === "number" && Number.isInteger(n) && n > 0 && n < 2 ** 31 ? n : null;
}

async function requireToken(): Promise<string> {
  const token = await getSessionToken();
  if (!token) throw new ApiError(401, "Please sign in first.");
  return token;
}

async function run(fn: (token: string) => Promise<unknown>, paths: string[]): Promise<ActionResult> {
  try {
    await fn(await requireToken());
  } catch (error) {
    if (error instanceof ApiError && error.status < 500) return { ok: false, error: error.message };
    console.error("Watchlist action failed", error);
    return { ok: false, error: "Something went wrong. Please try again." };
  }
  for (const path of paths) revalidatePath(path);
  return { ok: true };
}

export async function createWatchlist(_prev: ActionResult | null, formData: FormData): Promise<ActionResult> {
  const raw = formData.get("name");
  const name = typeof raw === "string" ? raw.trim().replace(/\s+/g, " ") : "";
  if (!name || name.length > 100) return { ok: false, error: "Name must be 1–100 characters." };
  return run((token) => api.createWatchlist(token, name), ["/watchlist"]);
}

export async function deleteWatchlist(watchlistId: number): Promise<ActionResult> {
  const id = toId(watchlistId);
  if (!id) return { ok: false, error: "Invalid watchlist." };
  return run((token) => api.deleteWatchlist(token, id), ["/watchlist"]);
}

export async function addToWatchlist(watchlistId: number, marketId: number): Promise<ActionResult> {
  const wid = toId(watchlistId);
  const mid = toId(marketId);
  if (!wid || !mid) return { ok: false, error: "Invalid request." };
  return run((token) => api.addItem(token, wid, mid), ["/watchlist", `/markets/${mid}`]);
}

export async function removeFromWatchlist(watchlistId: number, marketId: number): Promise<ActionResult> {
  const wid = toId(watchlistId);
  const mid = toId(marketId);
  if (!wid || !mid) return { ok: false, error: "Invalid request." };
  return run((token) => api.removeItem(token, wid, mid), ["/watchlist", `/markets/${mid}`]);
}

/** Creates a watchlist and adds a market to it in one step (used from the market page). */
export async function createWatchlistWithMarket(name: string, marketId: number): Promise<ActionResult> {
  const clean = typeof name === "string" ? name.trim().replace(/\s+/g, " ") : "";
  const mid = toId(marketId);
  if (!clean || clean.length > 100 || !mid) return { ok: false, error: "Invalid request." };
  return run(
    async (token) => {
      const watchlist = await api.createWatchlist(token, clean);
      await api.addItem(token, watchlist.id, mid);
    },
    ["/watchlist", `/markets/${mid}`],
  );
}
