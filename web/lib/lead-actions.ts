/**
 * What an attorney can do next, per state.
 *
 * Deliberately a plain module, not part of the `"use client"` component: a server
 * component that imports a value from a client module receives a client-reference
 * proxy rather than the object, so the lookup silently yields `undefined` and the
 * button disappears. Keeping the table here means both sides read the real data.
 *
 * This mirrors the API's transition table; the API stays the authority, so a stale
 * entry here produces a 409, never an illegal state.
 */

import type { LeadState } from "@/lib/api";

export type NextAction = {
  target: LeadState;
  label: string;
  pendingLabel: string;
};

export const NEXT_ACTION: Partial<Record<LeadState, NextAction>> = {
  PENDING: { target: "REACHED_OUT", label: "Mark reached out", pendingLabel: "Saving…" },
  REACHED_OUT: { target: "QUALIFIED", label: "Mark qualified", pendingLabel: "Saving…" },
};
