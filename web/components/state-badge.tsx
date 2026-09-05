import type { LeadState } from "@/lib/api";

/** Token-driven; the semantics of each state are unchanged. */
const STYLES: Record<LeadState, string> = {
  PENDING: "bg-[var(--state-pending-bg)] text-[var(--state-pending)]",
  REACHED_OUT: "bg-[var(--state-reached-out-bg)] text-[var(--state-reached-out)]",
  QUALIFIED: "bg-[var(--state-qualified-bg)] text-[var(--state-qualified)]",
};

const LABELS: Record<LeadState, string> = {
  PENDING: "Pending",
  REACHED_OUT: "Reached out",
  QUALIFIED: "Qualified",
};

/** Colour-coded lead state. The label carries the meaning; colour only reinforces it. */
export function StateBadge({ state }: { state: LeadState }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${STYLES[state]}`}
    >
      {LABELS[state]}
    </span>
  );
}
