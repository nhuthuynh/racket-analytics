// "Looks like contact details" (ST-016; api-sprint-01 §5.4; sprint-01 §5 Participants test 3).
import { describe, expect, it } from 'vitest';
import { looksLikeContactDetails } from '@/lib/setup/contact';

describe('looksLikeContactDetails', () => {
  it.each(['carlos@example.com', ' ivy@x.co ', '+44 7700 900123', '(555) 123-4567', '0612.345.678'])(
    'flags %j',
    (v) => expect(looksLikeContactDetails(v)).toBe(true),
  );
  it.each(['Ivy', 'Carlos 2', 'Team 123456', '@carlos', 'a@b', 'Sam the 1st'])('does not flag %j', (v) =>
    expect(looksLikeContactDetails(v)).toBe(false),
  );
});
