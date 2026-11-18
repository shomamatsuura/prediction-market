import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse, type NextRequest } from "next/server";

/**
 * Sets a strict, nonce-based Content-Security-Policy on every page response and protects
 * signed-in-only routes. When Clerk keys are configured, Clerk's middleware builds the CSP
 * (adding the Clerk origins it needs); otherwise an equivalent policy is built here.
 */

const clerkEnabled = Boolean(
  process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY,
);
const isDev = process.env.NODE_ENV !== "production";
const isProtectedRoute = createRouteMatcher(["/watchlist(.*)"]);

const extraDirectives = {
  "img-src": ["data:", "blob:"],
  "font-src": ["self"],
  "object-src": ["none"],
  "base-uri": ["self"],
  "frame-ancestors": ["none"],
  "form-action": ["self"],
};

const withClerk = clerkMiddleware(
  async (auth, req) => {
    if (isProtectedRoute(req)) await auth.protect();
  },
  {
    contentSecurityPolicy: { strict: true, directives: extraDirectives },
  },
);

function withoutClerk(request: NextRequest) {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  const nonce = btoa(String.fromCharCode(...bytes));
  const csp = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${isDev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self'",
    `connect-src 'self'${isDev ? " ws: wss:" : ""}`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    ...(isDev ? [] : ["upgrade-insecure-requests"]),
  ].join("; ");

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);
  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export default clerkEnabled ? withClerk : withoutClerk;

export const config = {
  matcher: [
    // Pages (skip Next.js internals and static files).
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    // Clerk may proxy its Frontend API through these routes.
    "/(api|trpc)(.*)",
  ],
};
