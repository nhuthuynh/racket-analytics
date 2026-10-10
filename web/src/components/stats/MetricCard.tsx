'use client';

// One D-01 metric card (ST-048; flows-sprint-03 §2): a section named by the metric's name from the
// API, one block per side (your side first) with the value printed in words and its n, the
// low-sample tag and reason in text (FR-101), bars only beside printed rows (NFR-034), "Show me"
// per side (E-01, ST-047), and "How is this measured?" with the coach's definition (FR-102).
import { useId, useState } from 'react';
import type { Metric, Stats } from '@/lib/stats/types';
import {
  lowSampleReason,
  minSampleLine,
  mixRows,
  runRows,
  showMeText,
  sideHasSample,
  sideSummary,
  versionLine,
  type BarRow,
} from '@/lib/stats/view';
import type { Side } from '@/lib/tagging/types';
import type { SideNames } from '@/lib/tagging/view';
import { EvidencePanel } from './EvidencePanel';
import type { StatsApi } from './StatsDashboard';

export interface OpenEvidence {
  metricId: string;
  side: Side;
}

function Bars({ rows }: { rows: BarRow[] }) {
  return (
    <ul className="bar-list">
      {rows.map((r) => (
        <li key={r.key} className="bar-list__row">
          <span>{r.text}</span>
          <span className="bar" aria-hidden="true">
            <span className="bar__fill" style={{ inlineSize: `${Math.round(r.fraction * 100)}%` }} />
          </span>
        </li>
      ))}
    </ul>
  );
}

export function MetricCard({
  matchId,
  metric,
  stats,
  names,
  open,
  onToggle,
  api,
  onReload,
}: {
  matchId: string;
  metric: Metric;
  stats: Stats;
  names: SideNames;
  open: OpenEvidence | null;
  onToggle: (which: OpenEvidence) => void;
  api: StatsApi;
  onReload: () => void;
}) {
  const id = useId();
  const [howOpen, setHowOpen] = useState(false);
  const { entry } = metric;
  const order: Side[] = names.mySide === 'A' ? ['A', 'B'] : ['B', 'A'];
  const nickname = (slot: string) => names.players.find((p) => p.slot === slot)?.nickname ?? slot;

  return (
    <section className="stat-card" aria-labelledby={`${id}-name`}>
      <h2 id={`${id}-name`}>{entry.name}</h2>
      <div className="stat-card__sides">
        {order.map((side) => {
          const summary = sideSummary(metric, side, nickname);
          const low = metric[side].low_sample;
          const mine = side === names.mySide;
          const isOpen = open?.metricId === entry.id && open.side === side;
          const panelId = `${id}-evidence-${side}`;
          const words = showMeText(metric, side);
          return (
            <div key={side} className="stat-side" data-side={side}>
              <h3 className="stat-side__label">{names.label(side)}</h3>
              <p className={low ? 'stat-side__value stat-side__value--low' : 'stat-side__value'}>{summary.main}</p>
              {summary.lines.map((line) => (
                <p key={line}>{line}</p>
              ))}
              {metric.kind === 'mix' && metric[side].n > 0 ? <Bars rows={mixRows(metric[side])} /> : null}
              {metric.kind === 'runs' && metric[side].n > 0 ? <Bars rows={runRows(metric[side])} /> : null}
              {low ? (
                <p className="stat-side__low">
                  <span className="tag tag--warning">low sample</span> {lowSampleReason(entry, stats.lowSampleRule)}
                </p>
              ) : null}
              {sideHasSample(metric, side) ? (
                <>
                  <p>
                    <button
                      type="button"
                      className="button button--secondary stat-side__show"
                      aria-expanded={isOpen}
                      aria-controls={isOpen ? panelId : undefined}
                      aria-label={`${words}, ${entry.name}, ${mine ? 'your side' : 'other side'}`}
                      onClick={() => onToggle({ metricId: entry.id, side })}
                    >
                      {words}
                    </button>
                  </p>
                  {isOpen ? (
                    <EvidencePanel
                      id={panelId}
                      matchId={matchId}
                      metric={metric}
                      side={side}
                      sideWords={mine ? 'your side' : 'other side'}
                      sheetVersion={stats.sheetVersion}
                      api={api}
                      onReload={onReload}
                    />
                  ) : null}
                </>
              ) : (
                <p>No rallies behind this yet.</p>
              )}
            </div>
          );
        })}
      </div>
      <p>
        <button
          type="button"
          className="button button--secondary"
          aria-expanded={howOpen}
          aria-controls={`${id}-how`}
          onClick={() => setHowOpen((o) => !o)}
        >
          How is this measured?
        </button>
      </p>
      <div id={`${id}-how`} className="stack stat-card__how" hidden={!howOpen}>
        {howOpen ? (
          <>
            <p>{entry.definition}</p>
            <p>{minSampleLine(entry)}</p>
            <p>{versionLine(entry)}</p>
          </>
        ) : null}
      </div>
    </section>
  );
}
