'use client';

// Error summary [DPA/DESIGN-13]; component checklist §5: heading "There is a problem",
// focus on render, one link per field to its input.
import { useEffect, useRef, type ReactNode } from 'react';

export interface FieldError {
  /** id of the input the link moves focus to */
  field: string;
  message: string;
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

  useEffect(() => {
    ref.current?.focus();
  }, [errors, general]);

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
              <a
                href={`#${e.field}`}
                onClick={(event) => {
                  event.preventDefault();
                  document.getElementById(e.field)?.focus();
                }}
              >
                {e.message}
              </a>
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
