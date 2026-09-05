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
        <p>
          Your confirmation email includes a <strong>tracking code</strong>. You can use
          it any time to check where your submission is.
        </p>
        <p>There is nothing else you need to do right now.</p>
      </div>
      <div className="flex flex-col gap-3 sm:flex-row">
        <Link
          href="/status"
          className="rounded-md bg-gray-900 px-4 py-2 text-center text-sm font-medium text-white hover:bg-gray-700 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
        >
          Check your status
        </Link>
        <Link
          href="/"
          className="rounded-md border border-gray-300 px-4 py-2 text-center text-sm font-medium hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-900"
        >
          Back to home
        </Link>
      </div>
    </div>
  );
}
