// One not-found page for every miss, including another player's match (no existence oracle).
import Link from 'next/link';
import { headers } from 'next/headers';
import { PageTitle } from '@/components/PageTitle';

// Rendered per request (reading headers makes it dynamic) so its scripts carry the CSP nonce.
export default async function NotFound() {
  await headers();
  return (
    <div className="stack">
      <PageTitle>Page not found</PageTitle>
      <h1>Page not found</h1>
      <p>We could not find that page. If you typed the address, check it is correct.</p>
      <p>
        <Link href="/matches">Go to your matches</Link>
      </p>
    </div>
  );
}
