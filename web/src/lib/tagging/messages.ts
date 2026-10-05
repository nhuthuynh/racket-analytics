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
      default:
        return `The rally was not saved. Try again.${ref}`;
    }
  }
  return 'The rally was not saved. Try again.';
}
