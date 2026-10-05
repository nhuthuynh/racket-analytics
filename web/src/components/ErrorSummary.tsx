'use client';

// Error summary [DPA/DESIGN-13]; component checklist §5: heading "There is a problem",
// focus on render, one link per field to its input.
import Link from 'next/link';
import { useEffect, useRef, type ReactNode } from 'react';

export interface FieldError {
  /** id of the input the link moves focus to */
  field: string;
  message: string;
  /** A page to go to instead of a field, when the fix is elsewhere (e.g. "/matches"). */
  href?: string;
}

export function ErrorSummary({
  errors,
  general,
  children,
}: {
  errors: FieldError[];
  general?: string;
  /** Extra lines under the list, e.g. U-03's "Nothing from this file was saved." */
  children?: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);

  // Focus moves only when the messages change, not on every re-render: callers pass a new array
  // each render, and typing in the field must keep focus there (PD-R2-01; SC 3.2.2, NFR-034).
  const signature = JSON.stringify([errors.map((e) => [e.field, e.message, e.href ?? '']), general ?? '']);
  useEffect(() => {
    ref.current?.focus();
  }, [signature]);

  if (errors.length === 0 && !general) return null;

  return (
    <div
      className="error-summary"
      ref={ref}
      tabIndex={-1}
      role="alert"
      aria-labelledby="error-summary-title"
    >
      <h2 id="error-summary-title" className="error-summary__title">
        There is a problem
      </h2>
      {general ? <p>{general}</p> : null}
      {errors.length > 0 ? (
        <ul className="error-summary__list">
          {errors.map((e) => (
            <li key={e.field}>
              {e.href ? (
                <Link href={e.href}>{e.message}</Link>
              ) : (
                <a
                  href={`#${e.field}`}
                  onClick={(event) => {
                    event.preventDefault();
                    document.getElementById(e.field)?.focus();
                  }}
                >
                  {e.message}
                </a>
              )}
            </li>
          ))}
        </ul>
      ) : null}
      {children}
    </div>
  );
}

const ERROR_PREFIX = 'Error: ';

/** Prefix the page title with "Error: " while errors are shown (checklist §0, §5). */
export function useErrorTitle(hasErrors: boolean): void {
  useEffect(() => {
    const base = document.title.startsWith(ERROR_PREFIX)
      ? document.title.slice(ERROR_PREFIX.length)
      : document.title;
    document.title = hasErrors ? `${ERROR_PREFIX}${base}` : base;
  }, [hasErrors]);
}
