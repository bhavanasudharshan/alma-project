"use client";

import { useState, useTransition } from "react";

import { markReachedOut, type MarkResult } from "@/app/(internal)/leads/actions";

/**
 * "Mark reached out" button.
 *
 * A 409 comes back as `already`, which is shown as a neutral notice rather than an
 * error: the attorney asked for a state the lead is already in, and the list has been
 * revalidated, so nothing is wrong from their point of view.
 */
export function MarkReachedOut({ leadId }: { leadId: string }) {
  const [pending, startTransition] = useTransition();
  const [result, setResult] = useState<MarkResult | null>(null);

  const tone =
    result?.status === "error"
      ? "text-red-600 dark:text-red-400"
      : "text-gray-600 dark:text-gray-400";

  return (
    <div className="flex flex-col items-start gap-1">
      <button
        type="button"
        disabled={pending}
        onClick={() =>
          startTransition(async () => {
            setResult(await markReachedOut(leadId));
          })
        }
        className="rounded-md border border-gray-300 px-2.5 py-1.5 text-xs font-medium
                   hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60
                   dark:border-gray-700 dark:hover:bg-gray-900"
      >
        {pending ? "Saving…" : "Mark reached out"}
      </button>
      {result && (
        <span role="status" className={`text-xs ${tone}`}>
          {result.message}
        </span>
      )}
    </div>
  );
}
