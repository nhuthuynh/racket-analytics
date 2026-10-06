// G-01 How to film your match (ST-015; FR-020; flows §4). Every instruction is text with an
// illustration; the video adds nothing the checklist does not say (NFR-033, [DPA/DESIGN-09]).
import Link from 'next/link';
import { GuideIllustration } from '@/components/GuideIllustration';
import { GuideVideo } from '@/components/GuideVideo';
import { PageTitle } from '@/components/PageTitle';
import { BATTERY_NOTE, CAPTURE_GUIDE_ITEMS, CONSENT_LINE, SAFETY_LINE, SIXTY_FPS_HELP } from '@/lib/content/capture-guide';

export default function GuidePage() {
  return (
    <div className="stack">
      <PageTitle>How to film your match</PageTitle>
      <p>
        <Link href="/matches" className="back-link">
          Back to your matches
        </Link>
      </p>
      <h1>How to film your match</h1>
      <p>{`${CAPTURE_GUIDE_ITEMS.length} things to check before the first serve.`}</p>
      <ol className="guide-list" aria-label="Checklist">
        {CAPTURE_GUIDE_ITEMS.map((item) => (
          <li key={item.id} className="guide-list__item">
            <GuideIllustration item={item} />
            <div className="guide-list__text">
              <p className="guide-list__instruction">{item.instruction}</p>
              <p>{item.why}</p>
              {item.id === 'height' ? (
                <>
                  <p className="notice notice--warning">{SAFETY_LINE}</p>
                  <p className="notice notice--info">{CONSENT_LINE}</p>
                </>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
      <p>{BATTERY_NOTE}</p>
      <details className="disclosure">
        <summary>How to record at 60 fps on my phone</summary>
        <p>{SIXTY_FPS_HELP}</p>
      </details>
      <GuideVideo />
      <p>
        <Link href="/matches/new" className="button">
          Record your first match
        </Link>
      </p>
    </div>
  );
}
