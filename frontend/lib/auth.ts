import "server-only";

import { auth } from "@clerk/nextjs/server";

import { clerkEnabled } from "./config";

/** The signed-in user's Clerk session token, or null when signed out or auth is disabled. */
export async function getSessionToken(): Promise<string | null> {
  if (!clerkEnabled) return null;
  const { userId, getToken } = await auth();
  if (!userId) return null;
  return getToken();
}
