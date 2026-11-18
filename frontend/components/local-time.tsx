"use client";

import { useSyncExternalStore } from "react";

const subscribe = () => () => {};

/** Formats a timestamp in the viewer's time zone (renders nothing on the server). */
export function LocalTime({ iso, options }: { iso: string; options: Intl.DateTimeFormatOptions }) {
  const text = useSyncExternalStore(
    subscribe,
    () => new Date(iso).toLocaleString("en-US", options),
    () => null,
  );
  return text ? <time dateTime={iso}>{text}</time> : null;
}
