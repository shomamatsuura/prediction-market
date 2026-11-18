import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="grid place-items-center gap-4 py-24 text-center">
      <p className="text-gradient text-6xl font-semibold">404</p>
      <p className="text-muted-foreground">That page doesn&apos;t exist.</p>
      <Button asChild variant="secondary">
        <Link href="/">Back to dashboard</Link>
      </Button>
    </div>
  );
}
