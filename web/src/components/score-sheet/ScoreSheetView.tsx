'use client';

// The score sheet screen's client part (ST-030). Holds the sheet and its version, so the
// correction, undo and video stories (ST-031, ST-032, ST-037) change it in place.
import { useState } from 'react';
import type { Match } from '@/lib/api/types';
import type { ScoreSheet } from '@/lib/tagging/types';
import { ScoreSheetTable } from './ScoreSheetTable';

export function ScoreSheetView({
  match,
  initialSheet,
}: {
  match: Match;
  initialSheet: ScoreSheet;
  initialVersion: number;
}) {
  const [sheet] = useState(initialSheet);
  return <ScoreSheetTable match={match} sheet={sheet} />;
}
