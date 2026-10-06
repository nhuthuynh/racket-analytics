// Correction history H-01 (ST-031; FR-052): every change and every undo, newest last, in words.
// Values are tag values only (sides, endings, slots), never free text (match-aggregate §6).
import type { Match } from '@/lib/api/types';
import type { HistoryItem } from '@/lib/tagging/types';
import { historyText, sideNames } from '@/lib/tagging/view';

const timeFormat = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });

function at(iso: string): string | null {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : timeFormat.format(d);
}

export function CorrectionHistory({ items, match }: { items: readonly HistoryItem[]; match: Match }) {
  const names = sideNames(match);
  if (items.length === 0) return <p>No changes yet.</p>;
  return (
    <ol className="history-list" aria-label="Correction history">
      {items.map((item) => {
        const time = at(item.at);
        return (
          <li key={item.id}>
            {historyText(item, items, names)}
            {time ? <span className="history-list__time">{` at ${time}`}</span> : null}
          </li>
        );
      })}
    </ol>
  );
}
