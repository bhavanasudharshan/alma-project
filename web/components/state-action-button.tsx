"use client";

import { useState, useTransition } from "react";

import { changeLeadState, type MarkResult } from "@/app/(internal)/leads/actions";
import type { LeadState } from "@/lib/api";

/**
 * Advances a lead to the next state in the pipeline.
 *
 * Generic over the target state: adding QUALIFIED required a new row in the table
 * below, not a new component (E1).
 *
 * A 409 carrying `already_in_state` is shown as a neutral notice rather than an error
 * — the attorney asked for a state the lead is already in, the list has been
 * revalidated, and nothing is actually wrong.
 */
export function StateActionButton({
  leadId,
  target,
  label,
  pendingLabel,
}: {
  leadId: string;
  target: LeadState;
  label: string;
  pendingLabel: string;
}) {
  const [pending, startTransition] = useTransition();
  const [result, setResult] = useState<MarkResult | null>(null);

  const tone =
    result?.status === "error"
      ? "text-red-700"
      : "text-muted";

  return (
    <div className="flex flex-col items-start gap-1">
      <button
        type="button"
        disabled={pending}
        onClick={() =>
          startTransition(async () => {
            setResult(await changeLeadState(leadId, target));
          })
        }
        className="rounded-md border border-brand bg-surface px-2.5 py-1.5 text-xs font-semibold text-brand
                   hover:bg-brand-soft disabled:cursor-not-allowed disabled:opacity-60"
      >
        {pending ? pendingLabel : label}
      </button>
      {result && (
        <span role="status" className={`text-xs ${tone}`}>
          {result.message}
        </span>
      )}
    </div>
  );
}
