import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/format";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize",
  {
    variants: {
      variant: {
        default: "border-border bg-secondary/70 text-secondary-foreground",
        up: "border-up/20 bg-up/10 text-up",
        down: "border-down/20 bg-down/10 text-down",
        primary: "border-primary/25 bg-primary/10 text-primary",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export function Badge({
  className,
  variant,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
