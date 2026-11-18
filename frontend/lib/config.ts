import "server-only";

/** Base URL of the FastAPI backend, reachable from the Next.js server only. */
export const API_URL = (process.env.API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

export const clerkEnabled = Boolean(
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY,
);
