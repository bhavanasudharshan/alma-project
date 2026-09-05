/**
 * Shared zod schemas.
 *
 * The client form validates a `FileList` (what an `<input type="file">` yields), the
 * server action validates a `File` (what `FormData` yields). The field rules are
 * defined once and reused by both so the two can never drift.
 */

import { z } from "zod";

// SEC2(b): legacy .doc is OLE and macro-prone, dropped in P1 to match the API.
export const ALLOWED_RESUME_EXTENSIONS = [".pdf", ".docx"] as const;
export const MAX_RESUME_BYTES = 5 * 1024 * 1024;

const ALLOWED_RESUME_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

const name = (label: string) =>
  z
    .string()
    .trim()
    .min(1, `${label} is required`)
    .max(100, `${label} must be 100 characters or fewer`);

const email = z.string().trim().min(1, "Email is required").email("Enter a valid email address");

/** Mirrors the API's allow-list and size cap so the applicant sees errors immediately (S2). */
function checkResume<T extends z.ZodType<File>>(schema: T) {
  return schema
    .refine((file) => file.size > 0, "That file is empty — attach your CV or resume")
    .refine((file) => file.size <= MAX_RESUME_BYTES, "Your file must be 5 MB or smaller")
    .refine(
      (file) =>
        ALLOWED_RESUME_TYPES.includes(file.type) ||
        ALLOWED_RESUME_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext)),
      "Upload a PDF or DOCX file",
    );
}

/** Server-side shape: `FormData.get("resume")` is a `File`. */
export const leadFormSchema = z.object({
  first_name: name("First name"),
  last_name: name("Last name"),
  email,
  resume: checkResume(z.instanceof(File, { message: "Attach your CV or resume" })),
});

/** Client-side shape: a file input registers as a `FileList`. */
export const leadClientSchema = z.object({
  first_name: name("First name"),
  last_name: name("Last name"),
  email,
  resume: checkResume(
    z
      .custom<FileList>()
      .refine((files) => files instanceof FileList && files.length === 1, "Attach your CV or resume")
      .transform((files) => files[0]),
  ),
});

/** What the inputs hold before validation (a file input yields a FileList). */
export type LeadClientInput = z.input<typeof leadClientSchema>;
/** What the resolver hands the submit handler (the FileList is now a File). */
export type LeadClientOutput = z.output<typeof leadClientSchema>;

export const loginSchema = z.object({
  email,
  password: z.string().min(1, "Password is required"),
});

export type LoginValues = z.infer<typeof loginSchema>;
