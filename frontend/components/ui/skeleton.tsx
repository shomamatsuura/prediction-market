import * as React from "react";

import { cn } from "@/lib/format";

export function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return <div className={cn("animate-pulse rounded-lg bg-white/[0.06]", className)} {...props} />;
}
