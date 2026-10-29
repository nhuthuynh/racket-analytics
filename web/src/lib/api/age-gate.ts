// Server pages and the FR-003 age gate (ST-068b). The flag comes from the API's public config;
// if it cannot be read the page behaves as with the flag off (the API still gates every route).
import { redirect } from 'next/navigation';
import { serverApi } from './server';
import { needsAgeAnswer } from './client';
import { AGE_QUESTION_PATH } from '@/lib/identity/age';

export async function ageGateOn(): Promise<boolean> {
  try {
    return (await (await serverApi()).publicConfig()).ageGate;
  } catch {
    return false;
  }
}

/** A 403 `age_confirmation_required` sends the holder to A-10 (flows-sprint-04 §5). */
export function askAgeIfNeeded(e: unknown): void {
  if (needsAgeAnswer(e)) redirect(AGE_QUESTION_PATH);
}
