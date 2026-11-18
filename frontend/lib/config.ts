import "server-only";

/** Base URL of the FastAPI backend, reachable from the Next.js server only. */
export const API_URL = (process.env.API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

/**
 * SECRET shared with the backend (never prefix with NEXT_PUBLIC_). With it, the backend rate
 * limits each visitor by their own IP instead of this server's, which all visitors share.
 */
export const INTERNAL_API_SECRET = process.env.INTERNAL_API_SECRET ?? "";

export const clerkEnabled = Boolean(
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY,
);
