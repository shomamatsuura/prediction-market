import { CloudOff, Inbox } from "lucide-react";

export function ApiUnavailable() {
  return (
    <div className="glass grid place-items-center gap-2 rounded-xl border border-border px-6 py-16 text-center">
      <CloudOff className="size-6 text-muted-foreground" />
      <p className="font-medium">Market data is unavailable right now</p>
      <p className="text-sm text-muted-foreground">The API didn&apos;t respond. Please try again in a moment.</p>
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="grid place-items-center gap-2 rounded-xl border border-dashed border-border px-6 py-14 text-center">
      <Inbox className="size-6 text-muted-foreground" />
      <p className="font-medium">{title}</p>
      {children ? <div className="text-sm text-muted-foreground">{children}</div> : null}
    </div>
  );
}
