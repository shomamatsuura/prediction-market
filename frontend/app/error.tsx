"use client";

import { Button } from "@/components/ui/button";

// Shown for unexpected errors. Error details are deliberately not rendered to the user.
export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="grid place-items-center gap-4 py-24 text-center">
      <p className="text-xl font-semibold">Something went wrong</p>
      <Button variant="secondary" onClick={reset}>
        Try again
      </Button>
    </div>
  );
}
