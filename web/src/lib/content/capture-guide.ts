// Capture guide wording (ST-015; FR-020). Copied unchanged from
// docs/domain/capture-guide-wording.md §1-§3 (coach draft 2026-10-03, sign-off due Sprint 1 D3).
// Filming advice, not a rule claim. Device-specific 60 fps steps stay out until checked on the
// ST-025 phones (wording §3, flows D-6).

export interface CaptureGuideItem {
  readonly id: 'tripod' | 'height' | 'landscape' | 'quality' | 'corners' | 'sun';
  readonly instruction: string;
  readonly why: string;
  /** Purpose description of the illustration (NFR-035). */
  readonly alt: string;
}

export const CAPTURE_GUIDE_ITEMS: readonly CaptureGuideItem[] = [
  {
    id: 'tripod',
    instruction: 'Put your phone on a tripod behind one baseline.',
    why: 'From behind the court we can see every rally from serve to the last shot.',
    alt: 'Phone on a tripod standing behind the middle of one baseline, facing the net.',
  },
  {
    id: 'height',
    instruction: 'Raise it as high as you safely can.',
    why: 'Height shows the far side of the court and the gap between players.',
    alt: 'Tripod extended to head height or above, with the whole far court visible over the net.',
  },
  {
    id: 'landscape',
    instruction: 'Turn the phone sideways (landscape).',
    why: 'The whole court fits across the screen.',
    alt: 'Phone held sideways on the tripod mount.',
  },
  {
    id: 'quality',
    instruction: 'Record in 1080p at 60 frames per second.',
    why: 'Fast shots stay sharp enough to see later.',
    alt: 'Camera settings screen with "1080p" and "60 fps" selected.',
  },
  {
    id: 'corners',
    instruction: 'Check that all four court corners are on screen.',
    why: 'If a corner is cut off, parts of the court cannot be analysed.',
    alt: 'Phone screen showing the whole court, with the four corners marked.',
  },
  {
    id: 'sun',
    instruction: 'Avoid filming towards the sun.',
    why: 'Bright light behind the court hides the ball and the players.',
    alt: 'Two small pictures: the sun behind the far court crossed out; the sun behind the camera ticked.',
  },
];

export const SAFETY_LINE =
  'Keep the tripod and its legs off the court and out of walkways. Never climb a fence or a chair to raise it.';

/**
 * D-8 consent courtesy line (PD-R2R-03): product-manager text, accepted unchanged by the
 * security-privacy-engineer (threat-model-sprint-02 §6). An instruction, not a legal claim; the
 * US/AU legal review (NFR-070) comes before any real-user beta.
 */
export const CONSENT_LINE = "Film only people who agree to be filmed. Don't upload matches with anyone under 18.";

export const BATTERY_NOTE =
  'A 90-minute match at 1080p 60 fps can use several gigabytes. Charge your phone and free up space first.';

export const SIXTY_FPS_HELP =
  "Open your camera's video settings and choose 1080p (also called Full HD) at 60 fps. If you can't find 60 fps, record at 30 fps: you can still tag your match, but some later results may be less accurate.";
