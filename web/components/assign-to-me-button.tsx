"use client";

import { useState, useTransition } from "react";

import { assignToMe, type MarkResult } from "@/app/(internal)/leads/actions";

/**
 * Claims an unassigned lead for the signed-in attorney (FR10).
 *
 * Only rendered on unassigned rows. Reassignment is deliberately API-only in this
 * slice, so there is no way to take a colleague's lead by accident.
 */
export function AssignToMeButton({ leadId }: { leadId: string }) {
  const [pending, startTransition] = useTransition();
  const [result, setResult] = useState<MarkResult | null>(null);

  return (
    <div className="flex flex-col items-start gap-1">
      <button
        type="button"
        disabled={pending}
        onClick={() =>
          startTransition(async () => {
            setResult(await assignToMe(leadId));
          })
        }
        className="rounded-md border border-line bg-surface px-2.5 py-1.5 text-xs font-medium
                   hover:bg-surface-sunken disabled:cursor-not-allowed disabled:opacity-60"
      >
        {pending ? "Assigning…" : "Assign to me"}
      </button>
      {result?.status === "error" && (
        <span role="status" className="text-xs text-red-700">
          {result.message}
        </span>
      )}
    </div>
  );
}
