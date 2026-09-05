import Link from "next/link";
import { redirect } from "next/navigation";
import type { Metadata } from "next";

import { StateActionButton } from "@/components/state-action-button";
import { NEXT_ACTION } from "@/lib/lead-actions";
import { StateBadge } from "@/components/state-badge";
import { ApiError, LEAD_STATES, listLeads, type LeadState } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { absoluteTime, relativeTime } from "@/lib/format";

export const metadata: Metadata = { title: "Leads — Alma" };

const PAGE_SIZE = 20;

const TABS: { label: string; state?: LeadState }[] = [
  { label: "Pending", state: "PENDING" },
  { label: "Reached out", state: "REACHED_OUT" },
  { label: "Qualified", state: "QUALIFIED" },
  { label: "All" },
];

function tabHref(state?: LeadState) {
  return state ? `/leads?state=${state}` : "/leads";
}

/** The attorney queue (FR5). Server component: the token never leaves the server. */
export default async function LeadsPage({
  searchParams,
}: {
  searchParams: Promise<{ state?: string; offset?: string }>;
}) {
  const token = await getToken();
  if (!token) redirect("/login");

  const params = await searchParams;
  const state = LEAD_STATES.includes(params.state as LeadState)
    ? (params.state as LeadState)
    : undefined;
  const offset = Math.max(0, Number.parseInt(params.offset ?? "0", 10) || 0);

  let page;
  try {
    page = await listLeads(token, { state, limit: PAGE_SIZE, offset });
  } catch (error) {
    // An expired or forged cookie gets a 401 from the API; send them to sign in.
    if (error instanceof ApiError && error.status === 401) redirect("/login");
    throw error;
  }

  const showing = page.items.length;
  const from = offset + 1;
  const to = offset + showing;
  // An offset past the end returns no rows even though total > 0; treat that as its
  // own empty state rather than rendering "Showing 21-20 of 4" over a headerless table.
  const isEmptyPage = showing === 0;
  const isPastEnd = isEmptyPage && page.total > 0;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-[32px] leading-tight font-semibold tracking-[-0.5px]">Leads</h1>
        <p className="text-sm text-muted">
          Newest first. Mark a lead after you have reached out.
        </p>
      </header>

      <nav aria-label="Filter by state" className="flex gap-1 border-b border-line">
        {TABS.map((tab) => {
          const active = tab.state === state;
          return (
            <Link
              key={tab.label}
              href={tabHref(tab.state)}
              aria-current={active ? "page" : undefined}
              className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${
                active
                  ? "border-brand text-brand"
                  : "border-transparent text-muted hover:text-ink"
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>

      {isEmptyPage ? (
        <div className="rounded-lg border border-dashed border-line bg-surface px-6 py-12 text-center">
          <p className="text-sm font-medium">
            {isPastEnd ? "Nothing on this page" : "No leads here yet"}
          </p>
          <p className="mt-1 text-sm text-muted">
            {isPastEnd
              ? `There ${page.total === 1 ? "is" : "are"} ${page.total} lead${page.total === 1 ? "" : "s"} in this view.`
              : state === "REACHED_OUT"
                ? "Leads you mark as reached out will appear here."
                : "New submissions from the public form will appear here."}
          </p>
          {isPastEnd && (
            <Link
              href={tabHref(state)}
              className="mt-3 inline-block text-sm font-medium underline underline-offset-4"
            >
              Back to the first page
            </Link>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-line bg-surface">
          <table className="w-full min-w-[52rem] text-left text-sm">
            <thead className="border-b border-line bg-surface-sunken text-xs uppercase tracking-wide text-muted">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">Name</th>
                <th scope="col" className="px-4 py-3 font-medium">Email</th>
                <th scope="col" className="px-4 py-3 font-medium">Submitted</th>
                <th scope="col" className="px-4 py-3 font-medium">State</th>
                <th scope="col" className="px-4 py-3 font-medium">Resume</th>
                <th scope="col" className="px-4 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {page.items.map((lead) => (
                <tr key={lead.id} className="align-top">
                  <td className="px-4 py-3 font-medium">
                    {lead.first_name} {lead.last_name}
                  </td>
                  <td className="px-4 py-3">
                    <a href={`mailto:${lead.email}`} className="text-brand hover:text-brand-hover">
                      {lead.email}
                    </a>
                  </td>
                  <td className="px-4 py-3 text-muted">
                    <span>{relativeTime(lead.created_at)}</span>
                    <br />
                    <span className="text-xs">{absoluteTime(lead.created_at)}</span>
                  </td>
                  <td className="px-4 py-3">
                    <StateBadge state={lead.state} />
                  </td>
                  <td className="px-4 py-3">
                    <a
                      href={`/api/leads/${lead.id}/resume`}
                      className="text-brand hover:text-brand-hover"
                      title={lead.resume_filename}
                    >
                      Download
                    </a>
                  </td>
                  <td className="px-4 py-3">
                    {NEXT_ACTION[lead.state] ? (
                      <StateActionButton leadId={lead.id} {...NEXT_ACTION[lead.state]!} />
                    ) : (
                      <span className="text-xs text-muted">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!isEmptyPage && (
        <div className="flex items-center justify-between gap-4">
          <p className="text-sm text-muted">
            Showing {from}–{to} of {page.total}
          </p>
          <div className="flex gap-2">
            <PageLink
              label="Previous"
              state={state}
              offset={Math.max(0, offset - PAGE_SIZE)}
              disabled={offset === 0}
            />
            <PageLink
              label="Next"
              state={state}
              offset={offset + PAGE_SIZE}
              disabled={to >= page.total}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function PageLink({
  label,
  state,
  offset,
  disabled,
}: {
  label: string;
  state?: LeadState;
  offset: number;
  disabled: boolean;
}) {
  const classes = "rounded-md border px-3 py-1.5 text-sm font-medium";
  if (disabled) {
    return (
      <span
        aria-disabled="true"
        className={`${classes} border-line text-muted opacity-50`}
      >
        {label}
      </span>
    );
  }
  const query = new URLSearchParams();
  if (state) query.set("state", state);
  if (offset > 0) query.set("offset", String(offset));
  return (
    <Link
      href={`/leads${query.toString() ? `?${query}` : ""}`}
      className={`${classes} border-line bg-surface hover:bg-surface-sunken`}
    >
      {label}
    </Link>
  );
}
