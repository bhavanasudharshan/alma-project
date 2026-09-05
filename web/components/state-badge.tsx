import type { LeadState } from "@/lib/api";

const STYLES: Record<LeadState, string> = {
  PENDING:
    "bg-amber-100 text-amber-900 ring-amber-200 dark:bg-amber-950 dark:text-amber-200 dark:ring-amber-900",
  REACHED_OUT:
    "bg-emerald-100 text-emerald-900 ring-emerald-200 dark:bg-emerald-950 dark:text-emerald-200 dark:ring-emerald-900",
};

const LABELS: Record<LeadState, string> = {
  PENDING: "Pending",
  REACHED_OUT: "Reached out",
};

/** Colour-coded lead state. The label carries the meaning; colour only reinforces it. */
export function StateBadge({ state }: { state: LeadState }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STYLES[state]}`}
    >
      {LABELS[state]}
    </span>
  );
}
