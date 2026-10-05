// Score sheet S-01 (ST-030; FR-049, FR-055; DES FR-UX-70). One semantic table per game with a
// caption, column headers and the rally number as row header. At narrow widths the CSS stacks
// each row into labelled lines; the explicit ARIA roles keep the table semantics when the
// display changes (WebKit drops them otherwise). Markers are words, never colour alone
// (NFR-034). The unofficial label is on every sheet while the server says unofficial (FR-055).
import Link from 'next/link';
import type { ReactNode } from 'react';
import type { Match } from '@/lib/api/types';
import { ENDING_LABELS, UNOFFICIAL_LABEL, type ScoreSheet, type SheetRow, type Side } from '@/lib/tagging/types';
import { formatClock, sideNames, type SideNames } from '@/lib/tagging/view';

const COLUMNS = ['Rally', 'Start', 'Server', 'Score before', 'Score after', 'Won by', 'Ending', 'Player', 'Notes'] as const;

function sideWord(side: Side, names: SideNames): string {
  return side === names.mySide ? 'Your side' : 'Other side';
}

function serverText(row: SheetRow, names: SideNames): string {
  if (!row.serving_side || !row.score_before) return 'Not scored';
  const server = /-([12])$/.exec(row.score_before)?.[1];
  return server ? `${sideWord(row.serving_side, names)}, server ${server}` : sideWord(row.serving_side, names);
}

function playerText(row: SheetRow, names: SideNames): string {
  if (row.ending === 'replay') return 'Not applicable';
  if (!row.responsible_player) return 'player not tagged';
  return names.players.find((p) => p.slot === row.responsible_player)?.nickname ?? row.responsible_player;
}

function notes(row: SheetRow): string[] {
  const out: string[] = [];
  if (row.corrected_by_user) out.push('corrected by you');
  if (row.marker === 'needs_decision') out.push('needs your decision');
  return out;
}

export function ScoreSheetTable({
  match,
  sheet,
  rowActions,
}: {
  match: Match;
  sheet: ScoreSheet;
  /** Extra controls per rally (corrections, video link), rendered in the Notes cell. */
  rowActions?: (row: SheetRow) => ReactNode;
}) {
  const names = sideNames(match);
  const games = [...new Set(sheet.rows.map((r) => r.game))].sort((a, b) => a - b);
  return (
    <div className="stack">
      {sheet.unofficial ? <p className="notice notice--warning score-sheet__label">{UNOFFICIAL_LABEL}</p> : null}
      <p className="score-sheet__rules">{`Rules: ${sheet.rules_version}`}</p>
      {sheet.rows.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state__title">No rallies tagged yet.</p>
          <p>
            <Link href={`/matches/${match.id}/tag`} className="button">
              Tag rallies
            </Link>
          </p>
        </div>
      ) : (
        games.map((game) => {
          const winner = sheet.games?.find((g) => g.number === game)?.winner ?? null;
          return (
            <table key={game} role="table" className="score-sheet">
              <caption role="caption" className="score-sheet__caption">
                {winner ? `Game ${game}, won by ${sideWord(winner, names).toLowerCase()}` : `Game ${game}`}
              </caption>
              <thead role="rowgroup">
                <tr role="row">
                  {COLUMNS.map((c) => (
                    <th key={c} role="columnheader" scope="col">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody role="rowgroup">
                {sheet.rows
                  .filter((r) => r.game === game)
                  .map((r) => {
                    const cells = [
                      formatClock(r.start_ms),
                      serverText(r, names),
                      r.score_before ?? 'Not scored',
                      r.score_after ?? 'Not scored',
                      r.winning_side ? sideWord(r.winning_side, names) : 'No one (replay)',
                      ENDING_LABELS[r.ending],
                      playerText(r, names),
                    ];
                    return (
                      <tr key={r.rally_id} role="row" className={r.marker ? 'score-sheet__row--conflict' : undefined}>
                        <th role="rowheader" scope="row" data-label="Rally">{`Rally ${r.number}`}</th>
                        {cells.map((text, i) => (
                          <td key={COLUMNS[i + 1]} role="cell" data-label={COLUMNS[i + 1]}>
                            <span>{text}</span>
                          </td>
                        ))}
                        <td role="cell" data-label="Notes">
                          <div>
                            {notes(r).map((n) => (
                              <strong key={n} className="score-sheet__marker">
                                {n}
                              </strong>
                            ))}
                            {rowActions ? rowActions(r) : null}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          );
        })
      )}
    </div>
  );
}
