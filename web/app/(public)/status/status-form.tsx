"use client";

import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import { StateBadge } from "@/components/state-badge";
import { absoluteTime, relativeTime } from "@/lib/format";

import { lookupStatus, type StatusState } from "./actions";

const STATE_COPY: Record<string, string> = {
  PENDING: "We have your submission and an attorney will review it.",
  REACHED_OUT: "An attorney has reached out to you — check your email.",
  QUALIFIED: "An attorney has reviewed your background and is taking your case forward.",
};

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white
                 hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-60
                 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
    >
      {pending ? "Checking…" : "Check status"}
    </button>
  );
}

export function StatusForm() {
  const [state, formAction] = useActionState<StatusState, FormData>(lookupStatus, {});

  return (
    <div className="flex flex-col gap-8">
      <form action={formAction} className="flex flex-col gap-3">
        <label htmlFor="code" className="text-sm font-medium">
          Tracking code
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            id="code"
            name="code"
            defaultValue={state.code ?? ""}
            autoComplete="off"
            spellCheck={false}
            placeholder="e.g. O4AIUTRWGIP6E5GYXU3G2WPOSADMWDIR"
            aria-invalid={Boolean(state.error)}
            aria-describedby={state.error ? "code-error" : "code-hint"}
            className="w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm
                       shadow-sm focus:border-gray-900 focus:outline-none focus:ring-1
                       focus:ring-gray-900 dark:border-gray-700 dark:bg-gray-950"
          />
          <SubmitButton />
        </div>
        <p id="code-hint" className="text-xs text-gray-600 dark:text-gray-400">
          It is in the confirmation email we sent when you applied.
        </p>
        {state.error && (
          <p id="code-error" role="alert" className="text-sm text-red-600 dark:text-red-400">
            {state.error}
          </p>
        )}
      </form>

      {state.status && (
        <section className="flex flex-col gap-5 rounded-md border border-gray-200 p-5 dark:border-gray-800">
          <div className="flex flex-wrap items-center gap-3">
            <StateBadge state={state.status.state} />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Updated {relativeTime(state.status.updated_at)}
            </span>
          </div>

          <p className="text-sm">{STATE_COPY[state.status.state] ?? "Your submission is being reviewed."}</p>

          <div className="flex flex-col gap-2">
            <h2 className="text-sm font-medium">Timeline</h2>
            <ol className="flex flex-col gap-2">
              {state.status.events.map((event) => (
                <li key={`${event.to_state}-${event.at}`} className="flex flex-wrap items-baseline gap-2 text-sm">
                  <StateBadge state={event.to_state} />
                  <span className="text-gray-600 dark:text-gray-400">
                    {absoluteTime(event.at)} · {relativeTime(event.at)}
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </section>
      )}
    </div>
  );
}
