import type { Metadata } from "next";

import { ApplyForm } from "./apply-form";

export const metadata: Metadata = {
  title: "Apply — Alma",
  description: "Submit your details and CV for an immigration assessment.",
};

/** The public lead form (FR1). No authentication, no token, nothing internal. */
export default function ApplyPage() {
  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">Get an assessment</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Share your details and CV. An attorney will review your background and reach out
          about next steps. Everything you send stays private.
        </p>
      </header>
      <ApplyForm />
    </div>
  );
}
