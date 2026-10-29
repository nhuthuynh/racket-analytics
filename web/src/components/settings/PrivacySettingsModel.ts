// R-01 Privacy settings (ST-071; FR-008, FR-009; flows-sprint-04 §6): the Identity context's
// privacy choices in its own words, free of React and HTTP. Texts are PM-4's interim register
// (interim-wording-sprint-04.md W-R*, W-C*; pending legal review, P16) and PD-4's screen words.

/** FR-008: days the review video is kept after analysis; null = "until I delete it". */
export type RetentionDays = number | null;

export interface RetentionSetting {
  days: RetentionDays;
  /** The choices the API offers (api-sprint-04 §5), in its order. */
  choices: RetentionDays[];
}

/** FR-009: training use of the player's matches; off unless the player turns it on. */
export interface TrainingConsent {
  optIn: boolean;
}

/** A match with a review video and when that video is deleted (`review_video_delete_at`). */
export interface ReviewVideo {
  matchId: string;
  title: string;
  deleteAt: string | null;
}

/** Which R-01 sections exist (`GET /config/public` features). */
export interface PrivacyFeatures {
  retention: boolean;
  consent: boolean;
}

/** Settings the API does not return (ADR 0023 OQ-07; ADR 0006 system rule); decisions ST-071. */
export const DEFAULT_RETENTION_DAYS = 90;
export const ORIGINAL_VIDEO_DAYS = 30;

export const WORDS = {
  title: 'Privacy settings',
  loading: 'Loading your privacy settings…',
  loadFailed: 'We could not load your privacy settings. Try again.',
  offline: 'You are offline. Connect to change these settings.',
  saveFailed: "We couldn't save your choice. Your old setting still applies. Try again.", // W-R11, W-C07
  retentionHeading: 'How long we keep your videos', // W-R01
  retentionIntro: 'You choose how long we keep the video you watch and tag. Your score sheet, stats and plan stay until you delete the match.', // W-R02
  systemRule: `We delete the file you uploaded ${ORIGINAL_VIDEO_DAYS} days after it is ready. The copy you watch is kept for the time you choose here.`, // W-R03
  saveRetention: 'Save video setting',
  retentionSaved: 'Saved. The new deletion dates are shown below.', // W-R10
  datesUnread: 'Your video setting is saved, but we could not load the new deletion dates. Reload the page to see them.', // no PM-4 row yet; decisions ST-071
  datesHeading: 'When each video is deleted',
  noVideos: 'You have no match videos yet.',
  consentHeading: 'Help improve the app', // W-C01
  consentLabel: 'Use my matches to improve the app', // W-C02
  consentExplain: 'If you turn this on, we may use your matches and tags to train and test our video tools. It stays off unless you turn it on.', // W-C03
  consentTurnOff: 'You can turn it off at any time. Then your matches go into no new training sets. Older training sets are not changed, and they are replaced at their next planned update.', // W-C04
  saveConsent: 'Save training choice',
  consentOn: 'Turned on. You can turn it off here at any time.', // W-C05
  consentOff: 'Turned off. Your matches will not be in any new training set.', // W-C06
} as const;

export function privacyPageExists(f: PrivacyFeatures): boolean {
  return f.retention || f.consent;
}

/** W-R04 / W-R05 / W-R06. */
export function retentionChoiceLabel(days: RetentionDays): string {
  if (days === null) return 'Until I delete it';
  return days === DEFAULT_RETENTION_DAYS ? `${days} days (default)` : `${days} days`;
}

/** W-R07 (a date shown in the player's time zone) or W-R08. */
export function reviewVideoLine(v: ReviewVideo): { prefix: string; iso: string } | { text: string } {
  return v.deleteAt === null ? { text: 'Video kept until you delete it' } : { prefix: 'Video will be deleted on ', iso: v.deleteAt };
}
