// A-10 Are you 18 or over? (ST-068b; FR-003; flows-sprint-04 §5). Exists only while the public
// config says the age gate is on (flag off → the app's not-found page). A confirmed holder goes to
// the matches, no session to sign-in; only a holder the API gates sees the question.
import { notFound, redirect } from 'next/navigation';
import { AgeQuestion } from '@/components/age/AgeQuestion';
import { ApiError, needsAgeAnswer } from '@/lib/api/client';
import { ageGateOn } from '@/lib/api/age-gate';
import { serverApi } from '@/lib/api/server';

export default async function AgeQuestionPage() {
  if (!(await ageGateOn())) notFound();
  try {
    await (await serverApi()).me();
  } catch (e) {
    if (needsAgeAnswer(e)) return <AgeQuestion />;
    if (e instanceof ApiError && e.status === 401) redirect('/');
    throw e;
  }
  redirect('/matches');
}
