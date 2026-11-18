import * as React from "react";

import { cn } from "@/lib/format";

export function Input({ className, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      className={cn(
        "h-10 w-full rounded-full border border-input bg-white/[0.03] px-4 text-sm placeholder:text-muted-foreground outline-none transition focus-visible:border-primary/50 focus-visible:ring-[3px] focus-visible:ring-ring/40",
        className,
      )}
      {...props}
    />
  );
}
