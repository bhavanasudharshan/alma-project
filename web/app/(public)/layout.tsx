import { SiteHeader } from "@/components/site-header";

/** Public chrome: header, centred column, nothing else. */
export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-surface-sunken">
      <SiteHeader />
      <main className="mx-auto w-full max-w-[720px] flex-1 px-6 py-12 sm:px-12 sm:py-16">
        {children}
      </main>
    </div>
  );
}
