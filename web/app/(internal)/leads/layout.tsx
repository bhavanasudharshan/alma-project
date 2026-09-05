import { redirect } from "next/navigation";

import { getToken, readNameUnverified, readSubjectUnverified } from "@/lib/auth";
import { LogoutButton } from "@/components/logout-button";

/** Internal chrome: who is signed in, and a way out. */
export default async function LeadsLayout({ children }: { children: React.ReactNode }) {
  const token = await getToken();
  if (!token) redirect("/login");

  // Prefer the display name from the token; fall back to the email for older sessions.
  const attorney = readNameUnverified(token) ?? readSubjectUnverified(token);
  const attorneyEmail = readSubjectUnverified(token);

  return (
    <div className="flex min-h-screen flex-col bg-surface-sunken">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
          <span className="text-[22px] font-bold tracking-[-0.5px] text-brand">alma</span>
          <div className="flex items-center gap-4">
            {attorney && (
              <span className="hidden text-sm text-muted sm:inline" title={attorneyEmail ?? undefined}>
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
