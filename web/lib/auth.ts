/**
 * Cookie helpers for the attorney session.
 *
 * The JWT lives in an httpOnly cookie so client-side JavaScript can never read it
 * (S1). Only server components, route handlers and server actions call these.
 */

import { cookies } from "next/headers";

export const TOKEN_COOKIE = "alma_token";

/** 8 hours, matching ACCESS_TOKEN_EXPIRE_MINUTES on the API. */
const MAX_AGE_SECONDS = 8 * 60 * 60;

/** Read the attorney's bearer token, or `null` when signed out. */
export async function getToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(TOKEN_COOKIE)?.value ?? null;
}

/** Persist the token. `secure` is enabled outside development. */
export async function setTokenCookie(token: string): Promise<void> {
  const store = await cookies();
  store.set(TOKEN_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: MAX_AGE_SECONDS,
  });
}

/** Clear the session cookie. */
export async function clearTokenCookie(): Promise<void> {
  const store = await cookies();
  store.delete(TOKEN_COOKIE);
}

/**
 * Read the `sub` claim without verifying the signature.
 *
 * Safe for display only: the API re-verifies the token on every request, so a forged
 * cookie yields a 401 there. Nothing is authorised on the basis of this value.
 */
function decodeClaimsUnverified(token: string): { sub?: string; name?: string } | null {
  const payload = token.split(".")[1];
  if (!payload) return null;
  try {
    const json = Buffer.from(payload.replace(/-/g, "+").replace(/_/g, "/"), "base64").toString();
    return JSON.parse(json) as { sub?: string; name?: string };
  } catch {
    return null;
  }
}

export function readSubjectUnverified(token: string): string | null {
  return decodeClaimsUnverified(token)?.sub ?? null;
}

/**
 * The attorney's display name, for the header and the "Mine" tab.
 *
 * Display only, like the subject: the API re-verifies the token and re-consults the
 * roster on every request, so a forged name changes nothing but the greeting.
 */
export function readNameUnverified(token: string): string | null {
  return decodeClaimsUnverified(token)?.name ?? null;
}
