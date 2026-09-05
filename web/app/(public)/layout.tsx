import Link from "next/link";

/** Minimal public chrome: wordmark only, no internal navigation. */
export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-gray-200 dark:border-gray-800">
        <div className="mx-auto flex max-w-2xl items-center px-6 py-4">
          <Link href="/" className="text-lg font-semibold tracking-tight">
            alma
          </Link>
        </div>
      </header>
      <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-12">{children}</main>
      <footer className="border-t border-gray-200 px-6 py-6 dark:border-gray-800">
        <p className="mx-auto max-w-2xl text-xs text-gray-500">
          Your information is used only to assess your case.
        </p>
      </footer>
    </div>
  );
}
