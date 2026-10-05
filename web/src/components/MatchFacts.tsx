// Match status and media facts (ST-010 with ST-009). Facts appear only after the probe.
import { QualityReport } from '@/components/QualityReport';
import { formatMediaSummary } from '@/lib/format';
import { FORMAT_LABELS, STATUS_LABELS, type Match } from '@/lib/api/types';

export function MatchFacts({ match }: { match: Match }) {
  const waitingForProbe = match.status === 'video_received' && match.media === null;

  return (
    <>
      <dl className="summary-list">
        <div className="summary-list__row">
          <dt>Format</dt>
          <dd>{FORMAT_LABELS[match.format]}</dd>
        </div>
        <div className="summary-list__row">
          <dt>Status</dt>
          <dd>{STATUS_LABELS[match.status]}</dd>
        </div>
      </dl>

      {waitingForProbe ? (
        <p role="status" className="notice notice--info">
          Reading the video. This usually takes less than a minute.
        </p>
      ) : null}

      {match.status === 'probe_failed' ? (
        <p className="notice notice--warning">
          The file may be damaged or in a format we do not support yet. Try recording again with
          your phone&rsquo;s camera app.
        </p>
      ) : null}

      {match.media ? (
        <section aria-labelledby="video-facts-title" className="stack">
          <h2 id="video-facts-title">About the video</h2>
          <p className="facts-line">{formatMediaSummary(match.media)}</p>
          <dl className="summary-list">
            <div className="summary-list__row">
              <dt>Frame rate type</dt>
              <dd>{match.media.vfr ? 'Variable' : 'Constant'}</dd>
            </div>
            <div className="summary-list__row">
              <dt>Audio</dt>
              <dd>{match.media.has_audio ? 'Yes' : 'No'}</dd>
            </div>
            <div className="summary-list__row">
              <dt>Video codec</dt>
              <dd>{match.media.video_codec}</dd>
            </div>
          </dl>
        </section>
      ) : null}
      {match.media ? <QualityReport media={match.media} /> : null}
    </>
  );
}
