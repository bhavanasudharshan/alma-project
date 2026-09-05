import { redirect } from "next/navigation";

import { getToken, readSubjectUnverified } from "@/lib/auth";
import { LogoutButton } from "@/components/logout-button";

/** Internal chrome: who is signed in, and a way out. */
export default async function LeadsLayout({ children }: { children: React.ReactNode }) {
  const token = await getToken();
  if (!token) redirect("/login");

  const attorney = readSubjectUnverified(token);

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-gray-200 dark:border-gray-800">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
          <span className="text-lg font-semibold tracking-tight">alma</span>
          <div className="flex items-center gap-4">
            {attorney && (
              <span className="hidden text-sm text-gray-600 sm:inline dark:text-gray-400">
                {attorney}
              </span>
            )}
            <LogoutButton />
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">{children}</main>
    </div>
  );
}
