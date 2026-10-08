// Messages for a tag, game start, correction or decision the server did not do (ST-027, ST-031,
// ST-032; api-sprint-02 §3, §4). They say what happened and what to do, and carry the support
// reference when the API gave one (NFR-058). A refusal that a retry can never fix
// (`rules_unavailable`, `scorebook_full`) never says "Try again" (HAX G1/G2; BE-RV1-FE-01).
import { ApiError } from '@/lib/api/client';
import type { FieldErrorCode } from '@/lib/api/types';

export const RULES_UNAVAILABLE_MESSAGE = 'Scoring for this match format is not available yet.';

function fieldCode(e: ApiError, ...codes: FieldErrorCode[]): FieldErrorCode | null {
  return e.fields.find((f) => codes.includes(f.code))?.code ?? null;
}

/** "this match cannot hold any more rallies|changes." (api-sprint-02 §3 Limits). */
function fullReason(e: ApiError): string {
  return fieldCode(e, 'too_many_rallies') ? 'this match cannot hold any more rallies.' : 'this match cannot hold any more changes.';
}

/** "too many changes in a short time. You can try again at 14:32." in the viewer's local time. */
function rateReason(e: ApiError, timeZone?: string): string {
  const at = e.retryAt ? new Date(e.retryAt) : null;
  if (!at || Number.isNaN(at.getTime())) return 'too many changes in a short time. Wait a minute, then try again.';
  const time = new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
    ...(timeZone ? { timeZone } : {}),
  }).format(at);
  return `too many changes in a short time. You can try again at ${time}.`;
}

const TIME_CODES: FieldErrorCode[] = ['time_after_video', 'out_of_game_order', 'end_before_start', 'time_invalid', 'overlaps_rally'];

/** Why the rally's times were refused (api-sprint-02 §4.2 `start_ms`/`end_ms` codes). */
function tagTimesReason(e: ApiError): string {
  switch (fieldCode(e, ...TIME_CODES)) {
    case 'time_after_video':
      return 'it ends after the end of the video. Mark its end again.';
    case 'out_of_game_order':
      return "its times fall among another game's rallies. Mark its start and end again.";
    case 'end_before_start':
      return 'it ends before it starts. Mark its start and end again.';
    case 'time_invalid':
      return 'its times are not valid. Mark its start and end again.';
    case 'overlaps_rally':
      return 'its times overlap another rally. Mark its start and end again.';
    default:
      return 'its times do not fit: they overlap another rally or another game. Mark its start and end again.';
  }
}

export function tagFailureMessage(e: unknown, timeZone?: string): string {
  if (e instanceof ApiError) {
    const ref = e.supportRef ? ` Reference: ${e.supportRef}` : '';
    switch (e.code) {
      case 'network_error':
        return 'The rally was not saved because the connection dropped. Try again.';
      case 'invalid_outcome':
        return 'The rally was not saved: check the winner, the ending and the player.';
      case 'invalid_rally':
        return `The rally was not saved: ${tagTimesReason(e)}`;
      case 'match_not_ready':
        return 'You can tag this match once its video is received.';
      case 'match_over':
        return 'The match is over.';
      case 'decision_needed':
        return 'Some rallies need your decision first. Open the score sheet to decide.';
      case 'game_not_started':
        return 'Start the game first: choose who serves first.';
      case 'rules_unavailable':
        return RULES_UNAVAILABLE_MESSAGE;
      case 'scorebook_full':
        return `The rally was not saved: ${fullReason(e)}`;
      case 'rate_limited':
        return `The rally was not saved: ${rateReason(e, timeZone)}`;
      default:
        return `The rally was not saved. Try again.${ref}`;
    }
  }
  return 'The rally was not saved. Try again.';
}

/** What T-02 says when "Start game n" is refused (api-sprint-02 §3 `POST …/games`). */
export function gameStartProblem(e: unknown, game: number, timeZone?: string): string {
  if (e instanceof ApiError) {
    const ref = e.supportRef ? ` Reference: ${e.supportRef}` : '';
    switch (e.code) {
      case 'rules_unavailable':
        return RULES_UNAVAILABLE_MESSAGE;
      case 'scorebook_full':
        return `Game ${game} was not started: ${fullReason(e)}`;
      case 'rate_limited':
        return `Game ${game} was not started: ${rateReason(e, timeZone)}`;
      case 'game_not_over':
        return `Game ${game} cannot start yet: the game before it is not over. Open the score sheet to check it.`;
      case 'match_over':
        return 'The match is over.';
      case 'network_error':
        return `Game ${game} could not be started because the connection dropped. Try again.`;
      default:
        return `Game ${game} could not be started. Try again.${ref}`;
    }
  }
  return `Game ${game} could not be started. Try again.`;
}

/** Why a time correction was refused (the same §4.2 codes, said about a saved rally). */
function correctionTimesReason(e: ApiError): string {
  switch (fieldCode(e, ...TIME_CODES)) {
    case 'time_after_video':
      return 'the rally would end after the end of the video.';
    case 'out_of_game_order':
      return "the rally would fall among another game's rallies.";
    case 'end_before_start':
      return 'the rally would end before it starts.';
    case 'overlaps_rally':
      return 'the rally would overlap another rally.';
    default:
      return 'the rally times are not valid.';
  }
}

/** What the player is told when a correction, undo or decision is not done (ST-031, ST-032). */
export function commandProblem(e: unknown, what: string, timeZone?: string): string {
  if (e instanceof ApiError) {
    const ref = e.supportRef ? ` Reference: ${e.supportRef}` : '';
    if (e.code === 'nothing_to_undo') return 'There is nothing to undo.';
    if (e.code === 'game_not_started') return 'Start the next game on the tagging screen first, then move the rally.';
    if (e.code === 'network_error') return `${what} failed because the connection dropped. Try again.`;
    if (e.code === 'invalid_outcome') return `${what} was refused: the winner, the ending and the player do not fit together.`;
    if (e.code === 'invalid_rally') return `${what} was refused: ${correctionTimesReason(e)}`;
    if (e.code === 'rules_unavailable') return RULES_UNAVAILABLE_MESSAGE;
    if (e.code === 'scorebook_full') return `${what} was not saved: ${fullReason(e)}`;
    if (e.code === 'rate_limited') return `${what} was not saved: ${rateReason(e, timeZone)}`;
    if (e.code === 'validation_failed') {
      switch (fieldCode(e, 'previous_game_over', 'not_first_in_game', 'not_last_in_game', 'no_previous_game', 'not_needed')) {
        case 'previous_game_over':
          return 'The previous game is already over, so the rally cannot move back into it. Remove the rally, or move it to the next game.';
        case 'not_first_in_game':
          return 'Only the first rally of a game can move back to the previous game. Decide that rally first.';
        case 'not_last_in_game':
          // C3-03 (PE-S2-R3-01): the server moves only the latest kept rally of a game forward.
          return 'Only the last rally of a game can move to the next game. Decide the later rallies first.';
        case 'no_previous_game':
          return 'There is no previous game to move this rally to.';
        case 'not_needed':
          return 'This rally no longer needs a decision.';
        default:
      }
    }
    return `${what} failed. Try again.${ref}`;
  }
  return `${what} failed. Try again.`;
}
