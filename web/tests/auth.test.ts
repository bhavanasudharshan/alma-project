/**
 * Session cookie helpers (`lib/auth.ts`) — S1.
 *
 * The JWT must be unreachable from client JavaScript, so the flags are the security
 * control here, not a detail: HttpOnly always, SameSite=Lax always, Path=/ always,
 * and Secure whenever the app is not running locally.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type CookieOptions = {
  httpOnly?: boolean;
  sameSite?: string;
  secure?: boolean;
  path?: string;
  maxAge?: number;
};

const store = {
  set: vi.fn<(name: string, value: string, options: CookieOptions) => void>(),
  get: vi.fn<(name: string) => { value: string } | undefined>(),
  delete: vi.fn<(name: string) => void>(),
};

vi.mock("next/headers", () => ({ cookies: async () => store }));

import {
  TOKEN_COOKIE,
  clearTokenCookie,
  getToken,
  readNameUnverified,
  readSubjectUnverified,
  setTokenCookie,
} from "@/lib/auth";

/** Render the recorded options the way they would appear in a Set-Cookie header. */
function flagString(options: CookieOptions): string {
  const flags: string[] = [];
  if (options.httpOnly) flags.push("HttpOnly");
  if (options.sameSite) {
    flags.push(`SameSite=${options.sameSite[0].toUpperCase()}${options.sameSite.slice(1)}`);
  }
  if (options.path) flags.push(`Path=${options.path}`);
  if (options.secure) flags.push("Secure");
  return flags.join("; ");
}

/** Set the cookie and hand back what the cookie store was actually told. */
async function capture(): Promise<[string, string, CookieOptions]> {
  await setTokenCookie("a.b.c");
  return store.set.mock.calls[0];
}

/** A token whose payload is `claims`, signed with nothing — display use only. */
function fakeToken(claims: Record<string, unknown>): string {
  return `header.${Buffer.from(JSON.stringify(claims)).toString("base64url")}.signature`;
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("the session cookie's name and flags (S1)", () => {
  it("is named alma_token", () => {
    expect(TOKEN_COOKIE).toBe("alma_token");
  });

  it("writes the token under that name", async () => {
    const [name, value] = await capture();
    expect(name).toBe("alma_token");
    expect(value).toBe("a.b.c");
  });

  it("is HttpOnly, SameSite=Lax and Path=/ locally, with no Secure flag", async () => {
    vi.stubEnv("NODE_ENV", "development");
    const [, , options] = await capture();
    expect(options.httpOnly).toBe(true);
    expect(options.sameSite).toBe("lax");
    expect(options.path).toBe("/");
    expect(options.secure).toBe(false);
    expect(flagString(options)).toBe("HttpOnly; SameSite=Lax; Path=/");
  });

  it("adds Secure once the app is not local", async () => {
    vi.stubEnv("NODE_ENV", "production");
    const [, , options] = await capture();
    expect(options.secure).toBe(true);
    expect(flagString(options)).toBe("HttpOnly; SameSite=Lax; Path=/; Secure");
  });

  it("expires with the token it carries (8 hours, matching the API)", async () => {
    const [, , options] = await capture();
    expect(options.maxAge).toBe(8 * 60 * 60);
  });
});

describe("reading and clearing the session", () => {
  it("returns the token when the cookie is present", async () => {
    store.get.mockReturnValueOnce({ value: "a.b.c" });
    expect(await getToken()).toBe("a.b.c");
    expect(store.get).toHaveBeenCalledWith("alma_token");
  });

  it("returns null when the cookie is absent", async () => {
    store.get.mockReturnValueOnce(undefined);
    expect(await getToken()).toBeNull();
  });

  it("clears by name on sign-out", async () => {
    await clearTokenCookie();
    expect(store.delete).toHaveBeenCalledWith("alma_token");
  });
});

describe("unverified claim reading (display only)", () => {
  it("reads the subject and the display name", () => {
    const token = fakeToken({ sub: "attorney@example.com", name: "Alex Chen" });
    expect(readSubjectUnverified(token)).toBe("attorney@example.com");
    expect(readNameUnverified(token)).toBe("Alex Chen");
  });

  it("survives base64url payloads containing - and _", () => {
    const token = fakeToken({ sub: "a+b/c@example.com", name: "Ünïcode ??" });
    expect(readSubjectUnverified(token)).toBe("a+b/c@example.com");
  });

  it("returns null for a claim that is not there", () => {
    expect(readNameUnverified(fakeToken({ sub: "attorney@example.com" }))).toBeNull();
  });

  for (const [label, token] of [
    ["a token with no payload segment", "header"],
    ["a payload that is not base64", "header.!!!.signature"],
    ["a payload that is not JSON", `header.${Buffer.from("nope").toString("base64url")}.sig`],
    ["an empty string", ""],
  ] as const) {
    it(`returns null for ${label} rather than throwing`, () => {
      expect(readSubjectUnverified(token)).toBeNull();
      expect(readNameUnverified(token)).toBeNull();
    });
  }
});
