/**
 * Route guard for the internal area (S1).
 *
 * A cookie check only -- it decides whether to render or redirect, never what data is
 * returned. The API re-verifies the JWT signature on every request, so a forged cookie
 * gets past this and is then rejected with a 401 upstream.
 */

import { NextResponse, type NextRequest } from "next/server";

import { TOKEN_COOKIE } from "@/lib/auth";

export function middleware(request: NextRequest) {
  if (request.cookies.has(TOKEN_COOKIE)) return NextResponse.next();

  const login = new URL("/login", request.url);
  // Preserve where they were heading so login can send them back.
  login.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
  return NextResponse.redirect(login);
}

export const config = { matcher: ["/leads/:path*", "/leads"] };
