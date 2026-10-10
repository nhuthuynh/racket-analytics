// A-05 You have signed out (ST-014; flows-sprint-01 §2) and X-03 Your account has been deleted
// (ST-051; flows-sprint-03 §5). The device was cleared before this page loaded (AccountMenu,
// DeleteAccount). `?server=unreachable`: the server call failed, the local clear did not.
// The words never promise more than the clean-up does: browser history and files the user saved
// stay (DR-03 R3-7, SEC-S3-TM-12).
import Link from 'next/link';
import { PageTitle } from '@/components/PageTitle';

type Props = { searchParams: Promise<{ server?: string; deleted?: string }> };

export default async function SignedOutPage({ searchParams }: Props) {
  const { server, deleted } = await searchParams;
  const title = deleted === '1' ? 'Your account has been deleted' : 'You have signed out';
  return (
    <div className="stack">
      <PageTitle>{title}</PageTitle>
      <h1>{title}</h1>
      <p>
        {deleted === '1'
          ? "The app's data on this device has been cleared. Its stored files are removed within 7 days."
          : server === 'unreachable'
            ? "You have signed out on this device. We couldn't reach the server; your session will end on its own."
            : "The app's data on this device has been cleared."}
      </p>
      <p>
        <Link href="/" className="button">
          Sign in
        </Link>
      </p>
    </div>
  );
}
