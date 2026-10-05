// F-01 What this app does (ST-015; FR-004 with the flows D-1 R1 copy correction; HAX G1, G2).
// Static: no data, works offline. Release 1 has no computer vision (ADR 0002): the player marks
// who won each rally and the app keeps the score, which is unofficial until the rules are
// verified (FR-055, ADR 0009).
import Link from 'next/link';
import { PageTitle } from '@/components/PageTitle';

export default function WelcomePage() {
  return (
    <div className="stack">
      <PageTitle>What Racket Analytics does</PageTitle>
      <h1>What Racket Analytics does</h1>
      <p>
        <strong>You</strong> mark who won each rally while you watch your video. <strong>We</strong> keep
        the score and show where your points are won and lost.
      </p>
      <p>We can&apos;t make line calls or referee your match from one phone.</p>
      <p>
        Scores follow rules that are <strong>not yet checked against the official rulebook</strong>, so
        they are marked &lsquo;unofficial&rsquo;.
      </p>
      <p>Only you can see your videos.</p>
      <p>
        <Link href="/guide" className="button">
          Show me how to film
        </Link>
      </p>
      <p>
        <Link href="/matches/new" className="inline-target">
          Record your first match
        </Link>
      </p>
    </div>
  );
}
