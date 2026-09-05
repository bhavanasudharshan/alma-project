/** Presentation helpers shared by the queue. */

const ABSOLUTE = new Intl.DateTimeFormat("en-US", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** Absolute timestamp, e.g. "Jan 3, 2026, 09:15". */
export function absoluteTime(iso: string): string {
  return ABSOLUTE.format(new Date(iso));
}

/**
 * Coarse relative time, e.g. "2 hours ago".
 *
 * Computed on the server from a UTC timestamp. Deliberately coarse (no seconds) so a
 * server-rendered value does not look wrong by the time it reaches the browser.
 */
export function relativeTime(iso: string, now: Date = new Date()): string {
  const elapsed = now.getTime() - new Date(iso).getTime();
  if (elapsed < MINUTE) return "just now";
  if (elapsed < HOUR) {
    const minutes = Math.floor(elapsed / MINUTE);
    return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  }
  if (elapsed < DAY) {
    const hours = Math.floor(elapsed / HOUR);
    return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  }
  const days = Math.floor(elapsed / DAY);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}
