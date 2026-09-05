"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { FieldError } from "@/components/field-error";
import { loginSchema, type LoginValues } from "@/lib/validation";

const INPUT =
  "w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm " +
  "focus:border-gray-900 focus:outline-none focus:ring-1 focus:ring-gray-900 " +
  "dark:border-gray-700 dark:bg-gray-950 dark:focus:border-gray-100 dark:focus:ring-gray-100";

export function LoginForm({ next }: { next: string }) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);

    // Posts to our own route handler, which holds the token in an httpOnly cookie.
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });

    if (!response.ok) {
      const problem = (await response.json().catch(() => null)) as { detail?: string } | null;
      setFormError(problem?.detail ?? "Could not sign in. Please try again.");
      return;
    }

    router.push(next);
    router.refresh();
  });

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
      {formError && (
        <p
          role="alert"
          className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800
                     dark:border-red-900 dark:bg-red-950 dark:text-red-200"
        >
          {formError}
        </p>
      )}

      <div className="flex flex-col gap-1.5">
        <label htmlFor="email" className="text-sm font-medium">
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="username"
          aria-invalid={Boolean(errors.email)}
          aria-describedby={errors.email ? "email-error" : undefined}
          className={INPUT}
          {...register("email")}
        />
        <FieldError id="email-error" message={errors.email?.message} />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="password" className="text-sm font-medium">
          Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          aria-invalid={Boolean(errors.password)}
          aria-describedby={errors.password ? "password-error" : undefined}
          className={INPUT}
          {...register("password")}
        />
        <FieldError id="password-error" message={errors.password?.message} />
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white
                   hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-60
                   dark:bg-white dark:text-gray-900 dark:hover:bg-gray-200"
      >
        {isSubmitting ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
