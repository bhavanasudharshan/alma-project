"use server";

/** Server action for the public status portal (EXT1). No token, no account. */

import { ApiError, trackLead, type PublicLeadStatus } from "@/lib/api";

export type StatusState = {
  status?: PublicLeadStatus;
  error?: string;
  code?: string;
};

export async function lookupStatus(
  _previous: StatusState,
  formData: FormData,
): Promise<StatusState> {
  const code = String(formData.get("code") ?? "").trim();

  if (!code) {
    return { error: "Enter the tracking code from your confirmation email." };
  }

  try {
    return { status: await trackLead(code), code };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      // The API deliberately cannot tell malformed from unknown; neither do we.
      return { error: "We could not find a submission with that code. Check it and try again.", code };
    }
    if (error instanceof ApiError && error.status === 429) {
      return { error: "Too many lookups. Please wait a minute and try again.", code };
    }
    return { error: "Something went wrong looking that up. Please try again.", code };
  }
}
