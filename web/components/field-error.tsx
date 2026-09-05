/** Inline validation message, wired to its input by `aria-describedby`. */
export function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <p id={id} role="alert" className="text-[13px] text-red-700">
      {message}
    </p>
  );
}
