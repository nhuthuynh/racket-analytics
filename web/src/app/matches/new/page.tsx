// New match: title and format only (ST-010; participants arrive in Sprint 1).
import Link from 'next/link';
import { redirect } from 'next/navigation';
import { NewMatchForm } from '@/components/NewMatchForm';
import { PageTitle } from '@/components/PageTitle';
import { ApiError } from '@/lib/api/client';
import { serverApi } from '@/lib/api/server';

export default async function NewMatchPage() {
  try {
    await (await serverApi()).me();
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/');
    throw e;
  }
  return (
    <div className="stack">
      <PageTitle>New match</PageTitle>
      <p>
        <Link href="/matches" className="back-link">
          Back to your matches
        </Link>
      </p>
      <h1>New match</h1>
      <NewMatchForm />
    </div>
  );
}
