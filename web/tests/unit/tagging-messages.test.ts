// What the player is told when a tag is not saved (ST-027).
import { describe, expect, it } from 'vitest';
import { ApiError } from '@/lib/api/client';
import { tagFailureMessage } from '@/lib/tagging/messages';

describe('tagFailureMessage', () => {
  it('a non-API failure still says the rally was not saved', () => {
    expect(tagFailureMessage(new Error('boom'))).toBe('The rally was not saved. Try again.');
  });
  it('names the cause the player can act on', () => {
    expect(tagFailureMessage(new ApiError(0, 'network_error'))).toMatch(/connection dropped/);
    expect(tagFailureMessage(new ApiError(422, 'invalid_outcome'))).toMatch(/check the winner, the ending and the player/);
    expect(tagFailureMessage(new ApiError(422, 'invalid_rally'))).toMatch(/overlap another rally/);
    expect(tagFailureMessage(new ApiError(409, 'match_not_ready'))).toBe('You can tag this match once its video is received.');
    expect(tagFailureMessage(new ApiError(409, 'match_over'))).toBe('The match is over.');
  });
  it('carries the support reference of a server error', () => {
    expect(tagFailureMessage(new ApiError(500, 'internal_error', 'ref_0123456789abcdef'))).toBe(
      'The rally was not saved. Try again. Reference: ref_0123456789abcdef',
    );
  });
});
