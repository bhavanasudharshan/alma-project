import type { Metadata } from "next";

import { PRIVACY_NOTE } from "@/components/site-header";

import { ApplyForm } from "./apply-form";

export const metadata: Metadata = {
  title: "Apply — Alma",
  description: "Submit your details and résumé for review by an attorney.",
};

/** The public lead form (FR1). No authentication, no token, nothing internal. */
export default function ApplyPage() {
  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-[32px] leading-tight font-semibold tracking-[-0.5px]">Apply</h1>
        <p className="text-sm text-muted">
          Takes about two minutes. Fields marked * are required.
        </p>
      </header>

      <ApplyForm />

      <p className="text-[13px] text-muted">{PRIVACY_NOTE}</p>
    </div>
  );
}
