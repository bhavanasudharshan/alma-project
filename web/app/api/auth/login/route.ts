/**
 * Login route handler.
 *
 * Exists so the JWT never reaches client JavaScript: the browser posts credentials
 * here, this handler calls the API, and the token is written straight into an
 * httpOnly cookie (S1).
 */

import { NextResponse } from "next/server";

import { ApiError, login } from "@/lib/api";
import { setTokenCookie } from "@/lib/auth";
import { loginSchema } from "@/lib/validation";

export async function POST(request: Request) {
  const parsed = loginSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) {
    return NextResponse.json(
      { detail: parsed.error.issues[0]?.message ?? "Invalid request.", code: "validation_error" },
      { status: 422 },
    );
  }

  try {
    const { access_token } = await login(parsed.data.email, parsed.data.password);
    await setTokenCookie(access_token);
    return NextResponse.json({ ok: true });
  } catch (error) {
    if (error instanceof ApiError) {
      // Pass the API's deliberately vague message through unchanged (S4).
      return NextResponse.json(
        { detail: error.message, code: error.code },
        { status: error.status === 401 ? 401 : 502 },
      );
    }
    return NextResponse.json(
      { detail: "Could not reach the service. Please try again.", code: "upstream_unavailable" },
      { status: 502 },
    );
  }
}
