'use client';

// Unfinished-upload banner on M-01 (ST-017 U-04; flows §6; Gherkin "Return after closing the
// tab"). Server state is the source (match.upload), because sign-out clears the device.
import { useRouter } from 'next/navigation';
import type { Match } from '@/lib/api/types';

const keptUntil = new Intl.DateTimeFormat('en-GB', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
});

export function ResumeBanner({ matches }: { matches: Match[] }) {
  const router = useRouter();
  const unfinished = matches.filter((m) => m.upload?.state === 'receiving');
  if (unfinished.length === 0) return null;
  return (
    <div className="stack">
      {unfinished.map((m) => {
        const upload = m.upload!;
        const percent = upload.length > 0 ? Math.floor((upload.offset / upload.length) * 100) : 0;
        return (
          <section key={m.id} className="notice notice--info stack banner" aria-label="Unfinished upload">
            <p>{`Your upload of '${m.title}' is ${percent}% done.`}</p>
            <p>
              <button type="button" className="button" onClick={() => router.push(`/matches/${m.id}`)}>
                Resume upload
              </button>
            </p>
            <p>{`It will be kept until ${keptUntil.format(new Date(upload.expiresAt))}.`}</p>
          </section>
        );
      })}
    </div>
  );
}
