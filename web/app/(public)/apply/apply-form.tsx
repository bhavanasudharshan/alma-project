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
  "w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm " +
  "focus:border-gray-900 focus:outline-none focus:ring-1 focus:ring-gray-900 " +
  "dark:border-gray-700 dark:bg-gray-950 dark:focus:border-gray-100 dark:focus:ring-gray-100";

export function ApplyForm() {
  // Server-returned errors (the API rejected something the client could not know).
  const [serverState, setServerState] = useState<ApplyState>({});

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    // Three generics: input shape, context, transformed output shape.
  } = useForm<LeadClientInput, unknown, LeadClientOutput>({
    resolver: zodResolver(leadClientSchema),
  });

  const onSubmit = handleSubmit(async (values) => {
    const payload = new FormData();
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
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
      {serverState.formError && (
        <p
          role="alert"
          className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800
                     dark:border-red-900 dark:bg-red-950 dark:text-red-200"
        >
          {serverState.formError}
        </p>
      )}

      <div className="grid gap-5 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="first_name" className="text-sm font-medium">
            First name
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
          <label htmlFor="last_name" className="text-sm font-medium">
            Last name
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
        <label htmlFor="email" className="text-sm font-medium">
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          aria-invalid={Boolean(fieldError("email"))}
          aria-describedby={fieldError("email") ? "email-error" : undefined}
          className={INPUT}
          {...register("email")}
        />
        <FieldError id="email-error" message={fieldError("email")} />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="resume" className="text-sm font-medium">
          CV or resume
        </label>
        <input
          id="resume"
          type="file"
          accept={ALLOWED_RESUME_EXTENSIONS.join(",")}
          aria-invalid={Boolean(fieldError("resume"))}
          aria-describedby={fieldError("resume") ? "resume-error" : "resume-hint"}
          className="w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-gray-900
                     file:px-3 file:py-2 file:text-sm file:font-medium file:text-white
                     hover:file:bg-gray-700 dark:file:bg-white dark:file:text-gray-900"
          {...register("resume")}
        />
        <p id="resume-hint" className="text-xs text-gray-600 dark:text-gray-400">
          PDF, DOC or DOCX, up to 5 MB.
        </p>
        <FieldError id="resume-error" message={fieldError("resume")} />
      </div>

      <div>
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white
                     hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-60
                     dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
        >
          {isSubmitting ? "Submitting…" : "Submit application"}
        </button>
      </div>
    </form>
  );
}
