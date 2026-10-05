// Footage quality report (ST-019 stretch; FR-025; flows M-02). Never blocks (FR-UX-40). "You can
// still tag this match." follows a consequence finding only (C-20, PD-R2R-05).
import type { MediaFacts } from '@/lib/api/types';
import { qualityFindings } from '@/lib/quality';

export function QualityReport({ media }: { media: MediaFacts }) {
  const findings = qualityFindings(media);
  return (
    <section aria-labelledby="quality-title" className="stack">
      <h2 id="quality-title">Footage quality</h2>
      {findings.length === 0 ? (
        <p>Good: 1080p or better at 50 fps or more.</p>
      ) : (
        <ul className="quality-list">
          {findings.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
      )}
      {findings.length > 0 ? <p>You can still tag this match.</p> : null}
    </section>
  );
}
