import type { Metadata } from "next";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Sign in — Alma" };

/** Attorney sign-in (FR4). */
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const { next } = await searchParams;
  // Only accept a relative path, so ?next= cannot be used as an open redirect.
  const target = next && next.startsWith("/") && !next.startsWith("//") ? next : "/leads";

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-8 px-6 py-12">
      <header className="flex flex-col gap-2">
        <span className="text-lg font-semibold tracking-tight">alma</span>
        <h1 className="text-2xl font-semibold tracking-tight">Attorney sign in</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Access the lead intake queue.
        </p>
      </header>
      <LoginForm next={target} />
    </div>
  );
}
