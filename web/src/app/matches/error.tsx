'use client';

// Error state under /matches (C-30; flows-sprint-01 §5 M-01 "States"). The page puts the API's
// support reference into the error digest (Next keeps a digest the error already has), so the
// player can quote it; any other digest is not shown as a reference. Offline gets its own words.
import { usePathname } from 'next/navigation';
import { pageTitle } from '@/components/PageTitle';

const SUPPORT_REF = /^ref_[0-9a-f]{16}$/;

export default function MatchesError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const list = usePathname() === '/matches';
  const offline = typeof navigator !== 'undefined' && navigator.onLine === false;
  const ref = error.digest && SUPPORT_REF.test(error.digest) ? ` Reference: ${error.digest}` : '';
  const message = offline
    ? "You're offline. Your matches will appear when you reconnect."
    : `Sorry, we could not load ${list ? 'your matches' : 'this page'}. Try again.${ref}`;
  return (
    <div className="stack">
      <title>{`Error: ${pageTitle(list ? 'Your matches' : 'Sorry, there is a problem')}`}</title>
      <h1>{list ? 'Your matches' : 'Sorry, there is a problem'}</h1>
      <p role="alert" className="notice notice--error">
        {message}
      </p>
      <p>
        <button type="button" className="button" onClick={() => reset()}>
          Try again
        </button>
      </p>
    </div>
  );
}
