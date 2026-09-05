import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Thank you — Alma" };

/** Confirmation shown after a successful submission (FR1/FR2). */
export default function ThankYouPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold tracking-tight">Thank you — we have your details</h1>
      <div className="flex flex-col gap-3 text-sm text-gray-600 dark:text-gray-400">
        <p>
          A confirmation is on its way to your inbox, and an attorney has been notified. They
          will review your CV and contact you directly about next steps.
        </p>
        <p>There is nothing else you need to do right now.</p>
      </div>
      <Link href="/" className="text-sm font-medium underline underline-offset-4">
        Back to home
      </Link>
    </div>
  );
}
