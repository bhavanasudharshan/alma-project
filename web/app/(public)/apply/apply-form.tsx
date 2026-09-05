"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { FieldError } from "@/components/field-error";
import {
  ALLOWED_RESUME_EXTENSIONS,
  leadClientSchema,
  type LeadClientInput,
  type LeadClientOutput,
} from "@/lib/validation";

import { submitApplication, type ApplyState } from "./actions";

const INPUT =
  "w-full rounded-md border border-line bg-surface px-3 py-2.5 text-sm text-ink " +
  "placeholder:text-muted focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand";

const LABEL = "text-sm font-medium text-ink";

export function ApplyForm() {
  // Server-returned errors (the API rejected something the client could not know).
  const [serverState, setServerState] = useState<ApplyState>({});
  const [fileName, setFileName] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    // Three generics: input shape, context, transformed output shape.
  } = useForm<LeadClientInput, unknown, LeadClientOutput>({
    resolver: zodResolver(leadClientSchema),
  });

  const resumeField = register("resume");

  const onSubmit = handleSubmit(async (values, event) => {
    const payload = new FormData();
    // Not registered with react-hook-form: read it straight off the form element.
    const honeypot = new FormData(event?.target as HTMLFormElement).get("website");
    payload.set("website", typeof honeypot === "string" ? honeypot : "");
    payload.set("first_name", values.first_name);
    payload.set("last_name", values.last_name);
    payload.set("email", values.email);
    // zod transformed the FileList into a single File during validation.
    payload.set("resume", values.resume);

    // The action redirects to /thank-you on success; it only returns on failure.
    setServerState(await submitApplication({}, payload));
  });

  const fieldError = (field: keyof LeadClientInput) =>
    errors[field]?.message ?? serverState.fieldErrors?.[field];

  return (
    <form
      onSubmit={onSubmit}
      noValidate
      className="flex flex-col gap-6 rounded-lg border border-line bg-surface p-6 sm:p-8"
    >
      {serverState.formError && (
        <p
          role="alert"
          className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
        >
          {serverState.formError}
        </p>
      )}

      <fieldset className="flex flex-col gap-5">
        <legend className="mb-1 text-sm font-semibold text-ink">About you</legend>

        <div className="grid gap-5 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="first_name" className={LABEL}>
              First name <span aria-hidden="true">*</span>
            </label>
            <input
              id="first_name"
              autoComplete="given-name"
              aria-invalid={Boolean(fieldError("first_name"))}
              aria-describedby={fieldError("first_name") ? "first_name-error" : undefined}
              className={INPUT}
              {...register("first_name")}
            />
            <FieldError id="first_name-error" message={fieldError("first_name")} />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="last_name" className={LABEL}>
              Last name <span aria-hidden="true">*</span>
            </label>
            <input
              id="last_name"
              autoComplete="family-name"
              aria-invalid={Boolean(fieldError("last_name"))}
              aria-describedby={fieldError("last_name") ? "last_name-error" : undefined}
              className={INPUT}
              {...register("last_name")}
            />
            <FieldError id="last_name-error" message={fieldError("last_name")} />
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="email" className={LABEL}>
            Email <span aria-hidden="true">*</span>
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            aria-invalid={Boolean(fieldError("email"))}
            aria-describedby={fieldError("email") ? "email-error" : "email-hint"}
            className={INPUT}
            {...register("email")}
          />
          <p id="email-hint" className="text-[13px] text-muted">
            We&apos;ll send your confirmation and tracking code here.
          </p>
          <FieldError id="email-error" message={fieldError("email")} />
        </div>
      </fieldset>

      {/*
        SEC4 honeypot. Hidden from sighted users and from screen readers, and skipped
        by keyboard navigation, so a real applicant can never fill it in. Bots that
        auto-complete every field will, and the API silently drops those.
      */}
      <div aria-hidden="true" className="absolute left-[-9999px] h-0 w-0 overflow-hidden">
        <label htmlFor="website">Website (leave blank)</label>
        <input id="website" name="website" type="text" tabIndex={-1} autoComplete="off" />
      </div>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-sm font-semibold text-ink">Your résumé</legend>

        <label htmlFor="resume" className={LABEL}>
          Résumé <span aria-hidden="true">*</span>
        </label>

        {/* Styling only: still a plain file input underneath, no drag-and-drop script. */}
        <label
          htmlFor="resume"
          className="flex cursor-pointer flex-col items-center gap-1.5 rounded-md border border-dashed border-line bg-surface-sunken px-4 py-8 text-center hover:border-brand"
        >
          <span className="text-sm font-medium text-brand">
            {fileName ?? "Choose a file"}
          </span>
          <span id="resume-hint" className="text-[13px] text-muted">
            PDF or DOCX, up to 5 MB
          </span>
        </label>

        <input
          id="resume"
          type="file"
          accept={ALLOWED_RESUME_EXTENSIONS.join(",")}
          aria-invalid={Boolean(fieldError("resume"))}
          aria-describedby={fieldError("resume") ? "resume-error" : "resume-hint"}
          className="sr-only"
          {...resumeField}
          onChange={(event) => {
            resumeField.onChange(event);
            setFileName(event.target.files?.[0]?.name ?? null);
          }}
        />
        <FieldError id="resume-error" message={fieldError("resume")} />
      </fieldset>

      <div>
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-md bg-brand px-[22px] py-3 text-[15px] font-semibold text-white hover:bg-brand-hover disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Submitting…" : "Submit application"}
        </button>
      </div>
    </form>
  );
}
