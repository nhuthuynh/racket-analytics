'use client';

// Route wrapper for the setup flow (ST-016): client-side navigation keeps the chosen File in
// memory for the match page (src/lib/upload/handoff.ts), and "today" is the player's local date
// (flows Q-05), so the flow renders after mount rather than on the server.
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { MatchSetup, todayParts } from '@/components/MatchSetup';
import type { DateParts } from '@/lib/setup/flow';
import type { UploadPolicy } from '@/lib/api/types';

export function MatchSetupRoute({ policy }: { policy: UploadPolicy }) {
  const router = useRouter();
  const [today, setToday] = useState<DateParts | null>(null);
  useEffect(() => setToday(todayParts()), []);
  if (!today) return <p className="loading">Loading…</p>;
  return <MatchSetup policy={policy} today={today} navigate={(path) => router.push(path)} />;
}
