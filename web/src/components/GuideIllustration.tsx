// Capture-guide illustrations (ST-015; FR-020). Simple schematic SVGs drawn with token colours,
// each with a purpose description from the wording doc (NFR-035, [DPA/DESIGN-10]).
// Fixed viewBox and aspect ratio, so the list never shifts while it loads (flows G-01 Loading).
import type { ReactNode } from 'react';
import type { CaptureGuideItem } from '@/lib/content/capture-guide';

const DRAWINGS: Record<CaptureGuideItem['id'], ReactNode> = {
  tripod: (
    <>
      <rect x="20" y="10" width="80" height="60" className="ill-court" />
      <line x1="20" y1="40" x2="100" y2="40" className="ill-line" />
      <circle cx="60" cy="80" r="5" className="ill-accent" />
      <path d="M60 85 L52 92 M60 85 L68 92 M60 85 L60 93" className="ill-line" />
    </>
  ),
  height: (
    <>
      <line x1="10" y1="88" x2="110" y2="88" className="ill-line" />
      <rect x="70" y="62" width="4" height="26" className="ill-court" />
      <path d="M30 88 L30 20 M30 88 L18 88 M30 88 L42 88" className="ill-line" />
      <rect x="25" y="12" width="10" height="8" className="ill-accent" />
      <path d="M35 16 L110 60" className="ill-dash" />
    </>
  ),
  landscape: (
    <>
      <rect x="25" y="25" width="70" height="40" rx="5" className="ill-court" />
      <circle cx="88" cy="45" r="2" className="ill-accent" />
      <path d="M60 65 L60 90 M60 90 L48 96 M60 90 L72 96" className="ill-line" />
    </>
  ),
  quality: (
    <>
      <rect x="25" y="10" width="70" height="80" rx="6" className="ill-court" />
      <rect x="33" y="25" width="54" height="18" rx="3" className="ill-accent" />
      <text x="60" y="38" textAnchor="middle" className="ill-label">1080p</text>
      <rect x="33" y="55" width="54" height="18" rx="3" className="ill-accent" />
      <text x="60" y="68" textAnchor="middle" className="ill-label">60 fps</text>
    </>
  ),
  corners: (
    <>
      <rect x="10" y="20" width="100" height="60" rx="5" className="ill-court" />
      <path d="M35 70 L45 32 L75 32 L85 70 Z" className="ill-line" />
      <circle cx="35" cy="70" r="4" className="ill-accent" />
      <circle cx="45" cy="32" r="4" className="ill-accent" />
      <circle cx="75" cy="32" r="4" className="ill-accent" />
      <circle cx="85" cy="70" r="4" className="ill-accent" />
    </>
  ),
  sun: (
    <>
      <rect x="5" y="30" width="48" height="40" className="ill-court" />
      <circle cx="29" cy="22" r="8" className="ill-accent" />
      <path d="M8 33 L50 67 M50 33 L8 67" className="ill-line ill-line--thick" />
      <rect x="67" y="30" width="48" height="40" className="ill-court" />
      <circle cx="91" cy="82" r="8" className="ill-accent" />
      <path d="M78 50 L88 60 L104 40" className="ill-line ill-line--thick" />
    </>
  ),
};

export function GuideIllustration({ item }: { item: CaptureGuideItem }) {
  return (
    <svg
      role="img"
      aria-label={item.alt}
      viewBox="0 0 120 100"
      width="120"
      height="100"
      className="guide-illustration"
      focusable="false"
    >
      {DRAWINGS[item.id]}
    </svg>
  );
}
