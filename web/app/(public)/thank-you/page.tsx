import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Thank you — Alma" };

/**
 * Confirmation shown after a successful submission (FR1/FR2).
 *
 * The concept shows the tracking code large on this page. It is deliberately absent:
 * the submission redirects here without the code, and surfacing it would need either a
 * new API call or a change to the redirect — both are functional changes, and this
 * pass is presentational only. The code is in the confirmation email, and /status
 * accepts it. See "Questions for the architect".
 */
export default function ThankYouPage() {
  return (
    <div className="flex flex-col items-start gap-6">
      <span
        aria-hidden="true"
        className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-soft text-2xl leading-none text-brand"
      >
        ✓
      </span>

      <h1 className="text-[32px] leading-tight font-semibold tracking-[-0.5px]">
        Thanks — we&apos;ve received your application.
      </h1>

      <div className="flex flex-col gap-3 text-sm text-muted">
        <p>
          A confirmation email is on its way. It contains your{" "}
          <strong className="font-semibold text-ink">tracking code</strong> — save it to
          check your status later.
        </p>
        <p>
          An attorney will review your background and contact you directly about next
          steps. There is nothing else you need to do right now.
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Link
          href="/status"
          className="rounded-md bg-brand px-[22px] py-3 text-center text-[15px] font-semibold text-white hover:bg-brand-hover"
        >
          Check status
        </Link>
        <Link
          href="/"
          className="rounded-md border border-line bg-surface px-[22px] py-3 text-center text-[15px] font-medium hover:bg-surface-sunken"
        >
          Back to home
        </Link>
      </div>
    </div>
  );
}
