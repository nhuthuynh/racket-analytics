// Messages for a tag the server did not save (ST-027). They say what happened and what to do,
// and carry the support reference when the API gave one (NFR-058).
import { ApiError } from '@/lib/api/client';

export function tagFailureMessage(e: unknown): string {
  if (e instanceof ApiError) {
    const ref = e.supportRef ? ` Reference: ${e.supportRef}` : '';
    switch (e.code) {
      case 'network_error':
        return 'The rally was not saved because the connection dropped. Try again.';
      case 'invalid_outcome':
        return 'The rally was not saved: check the winner, the ending and the player.';
      case 'invalid_rally':
        return 'The rally was not saved: its times overlap another rally. Mark its start and end again.';
      case 'match_not_ready':
        return 'You can tag this match once its video is received.';
      case 'match_over':
        return 'The match is over.';
      case 'decision_needed':
        return 'Some rallies need your decision first. Open the score sheet to decide.';
      case 'game_not_started':
        return 'Start the game first: choose who serves first.';
      default:
        return `The rally was not saved. Try again.${ref}`;
    }
  }
  return 'The rally was not saved. Try again.';
}

/** What the player is told when a correction or undo is not done (ST-031, ST-032). */
export function commandProblem(e: unknown, what: string): string {
  if (e instanceof ApiError) {
    const ref = e.supportRef ? ` Reference: ${e.supportRef}` : '';
    if (e.code === 'nothing_to_undo') return 'There is nothing to undo.';
    if (e.code === 'game_not_started') return 'Start the next game on the tagging screen first, then move the rally.';
    if (e.code === 'network_error') return `${what} failed because the connection dropped. Try again.`;
    if (e.code === 'invalid_outcome') return `${what} was refused: the winner, the ending and the player do not fit together.`;
    return `${what} failed. Try again.${ref}`;
  }
  return `${what} failed. Try again.`;
}
