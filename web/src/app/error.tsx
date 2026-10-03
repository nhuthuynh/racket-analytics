'use client';

// Error state for every route (DoD UI). No internals are shown; the digest lets support
// match the server log line.
import { pageTitle } from '@/components/PageTitle';

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="stack">
      <title>{`Error: ${pageTitle('Sorry, there is a problem')}`}</title>
      <h1>Sorry, there is a problem with the service</h1>
      <p>Try again in a few minutes. Your matches and videos are safe.</p>
      {error.digest ? <p className="field__hint">Reference: {error.digest}</p> : null}
      <p>
        <button type="button" className="button" onClick={() => reset()}>
          Try again
        </button>
      </p>
    </div>
  );
}
