"use server";

/** Server actions for the attorney queue. The token is read from the httpOnly cookie. */

import { revalidatePath } from "next/cache";

import { ApiError, assignLead, updateLeadState, type LeadState } from "@/lib/api";
import { getToken, readSubjectUnverified } from "@/lib/auth";

export type MarkResult = {
  status: "ok" | "already" | "error";
  message: string;
};

/**
 * Move a lead to `target` (FR8).
 *
 * Generic over the target state on purpose: adding QUALIFIED needed no change here,
 * because the legal moves live in the API's transition table, not in the UI (E1).
 *
 * A 409 carrying `already_in_state` is not an error from the attorney's point of
 * view: someone (or another tab) already made the same change. The API's SQL guard
 * lets exactly one concurrent caller win, so the losers are looking at a stale row --
 * revalidate and say so calmly. A 409 with any other code is a genuinely illegal move
 * and is surfaced as an error.
 */
export async function changeLeadState(
  leadId: string,
  target: LeadState,
): Promise<MarkResult> {
  const token = await getToken();
  if (!token) {
    return { status: "error", message: "Your session expired. Please sign in again." };
  }

  try {
    await updateLeadState(token, leadId, target);
    revalidatePath("/leads");
    return { status: "ok", message: "Updated." };
  } catch (error) {
    // P1 split the 409 vocabulary. `already_in_state` means the lead is already where
    // the attorney wanted it — benign, so refresh and say so calmly. Any other 409 is a
    // move the pipeline forbids and is reported as a real problem.
    if (error instanceof ApiError && error.status === 409) {
      revalidatePath("/leads");
      if (error.code === "already_in_state") {
        return { status: "already", message: "Already in that state — list refreshed." };
      }
      return { status: "error", message: error.message };
    }
    if (error instanceof ApiError && error.status === 401) {
      return { status: "error", message: "Your session expired. Please sign in again." };
    }
    if (error instanceof ApiError && error.status === 404) {
      revalidatePath("/leads");
      return { status: "error", message: "That lead no longer exists." };
    }
    return { status: "error", message: "Could not update the lead. Please try again." };
  }
}


/**
 * Claim a lead for the signed-in attorney (FR10).
 *
 * The assignee is taken from the caller's own token rather than the form, so the
 * button cannot be used to assign work to somebody else. Reassignment is API-only in
 * this slice.
 */
export async function assignToMe(leadId: string): Promise<MarkResult> {
  const token = await getToken();
  if (!token) {
    return { status: "error", message: "Your session expired. Please sign in again." };
  }

  const me = readSubjectUnverified(token);
  if (!me) {
    return { status: "error", message: "Could not read your account. Please sign in again." };
  }

  try {
    await assignLead(token, leadId, me);
    revalidatePath("/leads");
    return { status: "ok", message: "Assigned to you." };
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      revalidatePath("/leads");
      return { status: "error", message: error.message };
    }
    if (error instanceof ApiError && error.status === 401) {
      return { status: "error", message: "Your session expired. Please sign in again." };
    }
    return { status: "error", message: "Could not assign the lead. Please try again." };
  }
}
