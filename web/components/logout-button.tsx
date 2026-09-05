"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

/** Clears the session cookie through the logout route handler. */
export function LogoutButton() {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  return (
    <button
      type="button"
      disabled={pending}
      onClick={async () => {
        setPending(true);
        await fetch("/api/auth/logout", { method: "POST" });
        router.push("/login");
        router.refresh();
      }}
      className="rounded-md border border-line bg-surface px-3 py-1.5 text-sm font-medium
                 hover:bg-surface-sunken disabled:opacity-60"
    >
      {pending ? "Signing out…" : "Log out"}
    </button>
  );
}
