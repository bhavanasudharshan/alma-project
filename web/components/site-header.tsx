import Link from "next/link";

/**
 * Public chrome: the wordmark and the attorney's way in.
 *
 * The wordmark is plain text in the accent colour — we do not reproduce logo artwork.
 */
export function SiteHeader() {
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-[720px] items-center justify-between gap-4 px-6 py-6 sm:px-12">
        <Link
          href="/"
          className="text-[22px] font-bold tracking-[-0.5px] text-brand"
        >
          alma
        </Link>
        <Link href="/login" className="text-sm text-muted hover:text-ink">
          Attorney sign in
        </Link>
      </div>
    </header>
  );
}

/** The privacy line that appears under the form and in the landing footer. */
export const PRIVACY_NOTE =
  "Your résumé is stored privately and is only visible to attorneys reviewing your submission.";
