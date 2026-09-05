import type { Metadata } from "next";

import { StatusForm } from "./status-form";

export const metadata: Metadata = {
  title: "Check your status — Alma",
  description: "Look up your submission with the tracking code from your email.",
};

/** Public status portal (EXT1): no account, just the code from the email. */
export default function StatusPage() {
  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">Check your status</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Enter the tracking code from your confirmation email. We will show where your
          submission is — nothing else is shown here, and no sign-in is needed.
        </p>
      </header>
      <StatusForm />
    </div>
  );
}
