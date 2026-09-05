"use server";

/** Server actions for the attorney queue. The token is read from the httpOnly cookie. */

import { revalidatePath } from "next/cache";

import { ApiError, updateLeadState } from "@/lib/api";
import { getToken } from "@/lib/auth";

export type MarkResult = {
  status: "ok" | "already" | "error";
  message: string;
};

/**
 * Mark a lead as reached out (FR8).
 *
 * A 409 is not an error from the attorney's point of view: it means someone (or
 * another tab) already made the same change. The API's SQL guard lets exactly one
 * concurrent caller win, so the losers are simply looking at a stale row -- revalidate
 * and say so calmly rather than showing a failure.
 */
export async function markReachedOut(leadId: string): Promise<MarkResult> {
  const token = await getToken();
  if (!token) {
    return { status: "error", message: "Your session expired. Please sign in again." };
  }

  try {
    await updateLeadState(token, leadId, "REACHED_OUT");
    revalidatePath("/leads");
    return { status: "ok", message: "Marked as reached out." };
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      revalidatePath("/leads");
      return { status: "already", message: "Already marked as reached out — list refreshed." };
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
