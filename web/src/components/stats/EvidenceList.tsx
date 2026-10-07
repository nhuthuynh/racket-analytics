// The rallies behind a stat, as links (E-01 and E-02; ST-047, flows-sprint-03 §3). Each opens the
// score sheet S-01 at that rally with its video (`?play=<rally_id>`, ADR 0043): the player can
// check the call and correct it in the same place (HAX G9). A client-side link keeps the tap's
// user activation, so the video may start playing on arrival (NFR-014).
import Link from 'next/link';
import type { EvidenceItem } from '@/lib/stats/types';
import { evidenceLabel } from '@/lib/stats/view';

export function sheetAt(matchId: string, rallyId: string): string {
  return `/matches/${matchId}/sheet?play=${rallyId}`;
}

export function EvidenceList({ matchId, items, label }: { matchId: string; items: EvidenceItem[]; label: string }) {
  if (items.length === 0) return <p>No rallies are behind this stat yet.</p>;
  return (
    <ul className="evidence-list" aria-label={label}>
      {items.map((item) => (
        <li key={item.rally_id}>
          <Link href={sheetAt(matchId, item.rally_id)} className="touch-link">
            {evidenceLabel(item)}
          </Link>
        </li>
      ))}
    </ul>
  );
}
