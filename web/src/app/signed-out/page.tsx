// A-05 You have signed out (ST-014; flows-sprint-01 §2). The device was cleared before this page
// loaded (AccountMenu). `?server=unreachable`: the server call failed, the local clear did not.
import Link from 'next/link';
import { PageTitle } from '@/components/PageTitle';

type Props = { searchParams: Promise<{ server?: string }> };

export default async function SignedOutPage({ searchParams }: Props) {
  const { server } = await searchParams;
  return (
    <div className="stack">
      <PageTitle>You have signed out</PageTitle>
      <h1>You have signed out</h1>
      <p>
        {server === 'unreachable'
          ? "You have signed out on this device. We couldn't reach the server; your session will end on its own."
          : 'Nothing from your account is kept on this device.'}
      </p>
      <p>
        <Link href="/" className="button">
          Sign in
        </Link>
      </p>
    </div>
  );
}
