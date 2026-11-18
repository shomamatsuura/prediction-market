export type Market = {
  id: number;
  question: string;
  slug: string | null;
  category: string;
  image_url: string | null;
  end_date: string | null;
  probability: number;
  volume: number;
  liquidity: number;
  active: boolean;
  updated_at: string;
};

export type MarketDetail = Market & { description: string | null };

export type MarketPage = { items: Market[]; total: number; limit: number; offset: number };

export type Snapshot = { probability: number; volume: number; captured_at: string };

export type Mover = { market: Market; previous_probability: number; change: number };

export type Category = { category: string; count: number };

export type WatchlistItem = { market: Market; added_at: string };

export type Watchlist = { id: number; name: string; created_at: string; items: WatchlistItem[] };

export type MarketSort = "volume" | "liquidity" | "probability" | "ending" | "updated";
