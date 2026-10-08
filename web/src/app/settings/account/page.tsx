// X-00 Your account (ST-051; flows-sprint-03 §5). Server component: a signed-out visitor goes to
// sign in. The design's "Signed in as <address>" line needs the address in `GET /me`, which the
// contract does not carry yet (decision-log 2026-10-07, routed to the principal-engineer).
import { redirect } from 'next/navigation';
import { DeleteAccount } from '@/components/DeleteAccount';
import { PageTitle } from '@/components/PageTitle';
import { ApiError } from '@/lib/api/client';
import { serverApi } from '@/lib/api/server';

export default async function AccountPage() {
  try {
    await (await serverApi()).me();
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/');
    throw e;
  }
  return (
    <div className="stack">
      <PageTitle>Your account</PageTitle>
      <h1>Your account</h1>
      <DeleteAccount />
    </div>
  );
}
