/**
 * Unit tests for the shared zod schemas (`lib/validation.ts`).
 *
 * Covers FR1/S2: every required field, the email format, the résumé allow-list and
 * the 5 MB cap at the exact boundary, plus SEC4 (the honeypot is the API's business,
 * never the schema's).
 */

import { describe, expect, it } from "vitest";

import {
  MAX_RESUME_BYTES,
  leadFormSchema,
  loginSchema,
} from "@/lib/validation";

/** A résumé of `size` bytes with the given name and declared content type. */
function file(name: string, type = "application/pdf", size = 1024): File {
  return new File([new Uint8Array(size)], name, { type });
}

const PDF = "application/pdf";
const DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
const BINARY = "application/octet-stream";

/** A valid submission, so each test can vary exactly one thing. */
function validInput(overrides: Record<string, unknown> = {}) {
  return {
    first_name: "Ada",
    last_name: "Lovelace",
    email: "ada@example.com",
    resume: file("cv.pdf", PDF),
    ...overrides,
  };
}

/** The first message zod produced for `field`, or undefined when it accepted it. */
function errorFor(input: Record<string, unknown>, field: string): string | undefined {
  const parsed = leadFormSchema.safeParse(input);
  if (parsed.success) return undefined;
  return parsed.error.issues.find((issue) => issue.path[0] === field)?.message;
}

describe("leadFormSchema — the happy path", () => {
  it("accepts a complete submission", () => {
    expect(leadFormSchema.safeParse(validInput()).success).toBe(true);
  });

  it("trims surrounding whitespace off the text fields", () => {
    const parsed = leadFormSchema.parse(
      validInput({ first_name: "  Ada  ", email: "  ada@example.com  " }),
    );
    expect(parsed.first_name).toBe("Ada");
    expect(parsed.email).toBe("ada@example.com");
  });
});

describe("leadFormSchema — required fields (FR1)", () => {
  for (const [field, label] of [
    ["first_name", "First name"],
    ["last_name", "Last name"],
    ["email", "Email"],
  ] as const) {
    it(`rejects an empty ${field}`, () => {
      expect(errorFor(validInput({ [field]: "" }), field)).toBe(`${label} is required`);
    });

    it(`rejects a whitespace-only ${field}`, () => {
      expect(errorFor(validInput({ [field]: "   " }), field)).toBe(`${label} is required`);
    });

    it(`rejects a missing ${field}`, () => {
      const input = validInput();
      delete (input as Record<string, unknown>)[field];
      expect(errorFor(input, field)).toBeDefined();
    });
  }

  it("caps a name at 100 characters", () => {
    expect(errorFor(validInput({ first_name: "a".repeat(101) }), "first_name")).toBe(
      "First name must be 100 characters or fewer",
    );
    expect(leadFormSchema.safeParse(validInput({ first_name: "a".repeat(100) })).success).toBe(
      true,
    );
  });
});

describe("leadFormSchema — email format (FR1)", () => {
  for (const bad of ["ada", "ada@", "@example.com", "ada example.com", "ada@example"]) {
    it(`rejects ${JSON.stringify(bad)}`, () => {
      expect(errorFor(validInput({ email: bad }), "email")).toBe("Enter a valid email address");
    });
  }

  for (const good of ["ada@example.com", "ada.lovelace+cv@sub.example.co.uk"]) {
    it(`accepts ${good}`, () => {
      expect(leadFormSchema.safeParse(validInput({ email: good })).success).toBe(true);
    });
  }
});

describe("leadFormSchema — résumé allow-list (S2, SEC2b)", () => {
  it("accepts a .pdf", () => {
    expect(leadFormSchema.safeParse(validInput({ resume: file("cv.pdf", PDF) })).success).toBe(
      true,
    );
  });

  it("accepts a .docx", () => {
    expect(leadFormSchema.safeParse(validInput({ resume: file("cv.docx", DOCX) })).success).toBe(
      true,
    );
  });

  it("accepts an uppercase extension", () => {
    expect(leadFormSchema.safeParse(validInput({ resume: file("CV.PDF", BINARY) })).success).toBe(
      true,
    );
  });

  for (const name of ["cv.doc", "cv.exe", "cv.pdf.exe", "cv", "cv.docx.exe"]) {
    it(`rejects ${name}`, () => {
      expect(errorFor(validInput({ resume: file(name, BINARY) }), "resume")).toBe(
        "Upload a PDF or DOCX file",
      );
    });
  }

  it("rejects a value that is not a File at all", () => {
    expect(errorFor(validInput({ resume: "cv.pdf" }), "resume")).toBe("Attach your CV or resume");
  });

  it("rejects an empty file", () => {
    expect(errorFor(validInput({ resume: file("cv.pdf", PDF, 0) }), "resume")).toBe(
      "That file is empty — attach your CV or resume",
    );
  });
});

describe("leadFormSchema — size limit at the boundary (S2)", () => {
  it("agrees with the API's 5 MB cap", () => {
    expect(MAX_RESUME_BYTES).toBe(5 * 1024 * 1024);
  });

  it("accepts exactly 5 MB", () => {
    const at = file("cv.pdf", PDF, MAX_RESUME_BYTES);
    expect(at.size).toBe(MAX_RESUME_BYTES);
    expect(leadFormSchema.safeParse(validInput({ resume: at })).success).toBe(true);
  });

  it("rejects 5 MB + 1 byte", () => {
    const over = file("cv.pdf", PDF, MAX_RESUME_BYTES + 1);
    expect(over.size).toBe(MAX_RESUME_BYTES + 1);
    expect(errorFor(validInput({ resume: over }), "resume")).toBe(
      "Your file must be 5 MB or smaller",
    );
  });
});

describe("leadFormSchema — honeypot (SEC4)", () => {
  it("ignores the honeypot field rather than validating it", () => {
    // The bot trap is the API's decision, not the schema's: a filled honeypot must
    // still parse here so the value can be forwarded untouched.
    const parsed = leadFormSchema.safeParse(validInput({ website: "http://spam.example" }));
    expect(parsed.success).toBe(true);
    expect(parsed.success && "website" in parsed.data).toBe(false);
  });

  it("parses fine when the honeypot is absent", () => {
    expect(leadFormSchema.safeParse(validInput()).success).toBe(true);
  });
});

describe("loginSchema (FR4)", () => {
  it("accepts credentials", () => {
    expect(loginSchema.safeParse({ email: "attorney@example.com", password: "pw" }).success).toBe(
      true,
    );
  });

  it("rejects an empty password", () => {
    const parsed = loginSchema.safeParse({ email: "attorney@example.com", password: "" });
    expect(parsed.success).toBe(false);
    expect(!parsed.success && parsed.error.issues[0].message).toBe("Password is required");
  });

  it("rejects a malformed email", () => {
    expect(loginSchema.safeParse({ email: "nope", password: "pw" }).success).toBe(false);
  });
});
