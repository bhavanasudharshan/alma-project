import Link from "next/link";

/** Landing page: the two entry points into the product. */
export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-8 px-6 py-16">
      <div className="flex flex-col gap-3">
        <span className="text-lg font-semibold tracking-tight">alma</span>
        <h1 className="text-3xl font-semibold tracking-tight">Immigration lead intake</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Prospective clients share their background; attorneys review and reach out.
        </p>
      </div>
      <nav className="flex flex-col gap-3 sm:flex-row">
        <Link
          href="/apply"
          className="rounded-md bg-gray-900 px-4 py-2 text-center text-sm font-medium text-white hover:bg-gray-700 dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
        >
          Apply for an assessment
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
