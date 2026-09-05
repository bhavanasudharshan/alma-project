import Link from "next/link";

import { PRIVACY_NOTE, SiteHeader } from "@/components/site-header";

const STEPS = [
  {
    title: "Submit your details and résumé",
    detail: "Four fields. About two minutes.",
  },
  {
    title: "Get a confirmation email",
    detail: "It includes a tracking code — keep it.",
  },
  {
    title: "An attorney reviews and reaches out",
    detail: "Check progress any time on the status page.",
  },
];

/** Landing page: what this is, and the one thing to do next. */
export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-surface-sunken">
      <SiteHeader />

      <main className="mx-auto flex w-full max-w-[720px] flex-1 flex-col gap-12 px-6 py-16 sm:px-12 sm:py-[72px]">
        <section className="flex flex-col gap-4">
          <h1 className="text-[40px] leading-[1.1] font-semibold tracking-[-1px]">
            Lead intake
          </h1>
          <p className="text-lg leading-relaxed text-muted">
            Prospective clients submit their details and résumé; an attorney reviews each
            submission and reaches out.
          </p>
          <div>
            <Link
              href="/apply"
              className="inline-block rounded-md bg-brand px-[22px] py-3 text-[15px] font-semibold text-white hover:bg-brand-hover"
            >
              Apply
            </Link>
          </div>
        </section>

        <section className="grid gap-8 sm:grid-cols-3">
          {STEPS.map((step, index) => (
            <div key={step.title} className="flex flex-col gap-2">
              <span
                aria-hidden="true"
                className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-soft text-sm font-bold text-brand"
              >
                {index + 1}
              </span>
              <h2 className="text-base font-semibold">{step.title}</h2>
              <p className="text-sm text-muted">{step.detail}</p>
            </div>
          ))}
        </section>

        <section className="flex flex-col gap-1.5 rounded-lg border border-line bg-surface px-6 py-5">
          <h2 className="text-sm font-semibold">Before you start</h2>
          <p className="text-sm text-muted">
            You&apos;ll need your name, an email address you check, and your résumé as PDF
            or DOCX (up to 5 MB).
          </p>
        </section>

        <footer className="flex flex-col gap-4 border-t border-line pt-6 sm:flex-row sm:items-center sm:justify-between">
          <Link href="/status" className="text-sm text-brand hover:text-brand-hover">
            Have a tracking code? Check your status →
          </Link>
          <p className="text-[13px] text-muted">{PRIVACY_NOTE}</p>
        </footer>
      </main>
    </div>
  );
}
