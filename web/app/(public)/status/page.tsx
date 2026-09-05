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
        <h1 className="text-[32px] leading-tight font-semibold tracking-[-0.5px]">
          Check your status
        </h1>
        <p className="text-sm text-muted">
          Enter the tracking code from your confirmation email.
        </p>
      </header>
      <StatusForm />
    </div>
  );
}
