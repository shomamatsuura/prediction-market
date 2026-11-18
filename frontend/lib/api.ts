import "server-only";

import { API_URL } from "./config";
import type {
  Category,
  MarketDetail,
  MarketPage,
  MarketSort,
  Mover,
  Snapshot,
  Watchlist,
} from "./types";

/**
 * Server-side client for the FastAPI backend. The browser never talks to the API directly:
 * pages and Server Actions call it from the Next.js server, so the session token stays server-side.
 */

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

type Query = Record<string, string | number | boolean | undefined | null>;

async function request<T>(
  path: string,
  { query, token, method = "GET", body }: { query?: Query; token?: string | null; method?: string; body?: unknown } = {},
): Promise<T> {
  const url = new URL(API_URL + path);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
  }
  const headers: Record<string, string> = { Accept: "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
    redirect: "error",
    signal: AbortSignal.timeout(10_000),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      if (typeof data?.detail === "string") detail = data.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function isNotFound(error: unknown) {
  return error instanceof ApiError && (error.status === 404 || error.status === 422);
}

export const api = {
  markets: (params: { q?: string; category?: string; sort?: MarketSort; limit?: number; offset?: number }) =>
    request<MarketPage>("/markets", { query: params }),
  market: (id: number) => request<MarketDetail>(`/markets/${id}`),
  snapshots: (id: number, days: number) => request<Snapshot[]>(`/markets/${id}/snapshots`, { query: { days } }),
  movers: (params: { hours?: number; limit?: number; direction?: "any" | "up" | "down" }) =>
    request<Mover[]>("/markets/movers", { query: params }),
  categories: () => request<Category[]>("/markets/categories"),

  watchlists: (token: string) => request<Watchlist[]>("/watchlists", { token }),
  createWatchlist: (token: string, name: string) =>
    request<Watchlist>("/watchlists", { token, method: "POST", body: { name } }),
  deleteWatchlist: (token: string, id: number) =>
    request<void>(`/watchlists/${id}`, { token, method: "DELETE" }),
  addItem: (token: string, watchlistId: number, marketId: number) =>
    request<Watchlist>(`/watchlists/${watchlistId}/items`, {
      token,
      method: "POST",
      body: { market_id: marketId },
    }),
  removeItem: (token: string, watchlistId: number, marketId: number) =>
    request<void>(`/watchlists/${watchlistId}/items/${marketId}`, { token, method: "DELETE" }),
};
