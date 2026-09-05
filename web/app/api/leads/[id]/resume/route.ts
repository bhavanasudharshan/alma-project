/**
 * Resume download proxy.
 *
 * The browser never holds the bearer token, so it cannot call the API's resume route
 * directly. This handler reads the httpOnly cookie server-side and streams the
 * response back, which also keeps resumes off any public URL (S1/C1).
 */

import { NextResponse } from "next/server";

import { ApiError, fetchResume } from "@/lib/api";
import { getToken } from "@/lib/auth";

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  const token = await getToken();
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated.", code: "not_authenticated" }, { status: 401 });
  }

  const { id } = await context.params;

  try {
    const upstream = await fetchResume(token, id);
    // Stream the body straight through; never buffer a resume in this process (P1).
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "application/octet-stream",
        "content-disposition": upstream.headers.get("content-disposition") ?? "attachment",
        // Resumes are PII: never let a shared cache hold one (C1).
        "cache-control": "private, no-store",
      },
    });
  } catch (error) {
    const status = error instanceof ApiError ? error.status : 502;
    const detail = error instanceof ApiError ? error.message : "Could not fetch the resume.";
    const code = error instanceof ApiError ? error.code : "upstream_unavailable";
    return NextResponse.json({ detail, code }, { status });
  }
}
