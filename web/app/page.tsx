import Link from "next/link";

/** Stage 0 landing page: entry points only, both targets arrive in P0. */
export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-8 px-6 py-16">
      <div className="flex flex-col gap-3">
        <h1 className="text-3xl font-semibold tracking-tight">Alma Lead Intake</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Scaffold only — the public form and the internal queue land in the next stage.
        </p>
      </div>

      <nav className="flex flex-col gap-3 sm:flex-row">
        <Link
          href="/apply"
          className="rounded-md bg-gray-900 px-4 py-2 text-center text-sm font-medium text-white hover:bg-gray-700 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
        >
          Apply
        </Link>
        <Link
          href="/leads"
          className="rounded-md border border-gray-300 px-4 py-2 text-center text-sm font-medium hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-900"
        >
          Attorney sign in
        </Link>
      </nav>
    </main>
  );
}
