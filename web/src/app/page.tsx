// A-01 Sign in or create an account (ST-013; flows-sprint-01 §2). A signed-in visitor goes
// straight to their matches. In dev/test only, the ST-006 test players are offered below the
// email form (the API answers 404 for /dev/users everywhere else, and nothing is shown).
import { redirect } from 'next/navigation';
import { SignInForm } from '@/components/SignInForm';
import { SignInPicker } from '@/components/SignInPicker';
import { ApiError } from '@/lib/api/client';
import { serverApi } from '@/lib/api/server';
import type { DevUser } from '@/lib/api/types';

async function signedIn(): Promise<boolean> {
  try {
    await (await serverApi()).me();
    return true;
  } catch {
    // 401, or the API is unreachable: show the form; sending a link reports any problem.
    return false;
  }
}

async function loadDevUsers(): Promise<DevUser[] | 'off' | 'unavailable'> {
  try {
    return await (await serverApi()).listDevUsers();
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) return 'off';
    return 'unavailable';
  }
}

export default async function SignInPage() {
  if (await signedIn()) redirect('/matches');
  const devUsers = await loadDevUsers();
  return (
    <div className="stack">
      <SignInForm />
      {devUsers === 'off' ? null : (
        <section aria-labelledby="dev-sign-in" className="stack panel">
          <h2 id="dev-sign-in">Test players (development only)</h2>
          {devUsers === 'unavailable' ? (
            <p className="notice notice--error">
              <span className="visually-hidden">Error: </span>
              Development sign-in is not available right now. Try again in a few minutes.
            </p>
          ) : (
            <SignInPicker users={devUsers} />
          )}
        </section>
      )}
    </div>
  );
}
