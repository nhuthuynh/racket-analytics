// Dev sign-in picker (ST-010 with ST-006). Replaced by email sign-in in Sprint 1.
import { PageTitle } from '@/components/PageTitle';
import { SignInPicker } from '@/components/SignInPicker';
import { ApiError } from '@/lib/api/client';
import { serverApi } from '@/lib/api/server';
import type { DevUser } from '@/lib/api/types';

async function loadUsers(): Promise<DevUser[] | 'unavailable'> {
  try {
    return await (await serverApi()).listDevUsers();
  } catch (e) {
    // 404: the dev provider is switched off, so there is nobody to pick.
    if (e instanceof ApiError && e.status === 404) return [];
    return 'unavailable';
  }
}

export default async function SignInPage() {
  const users = await loadUsers();
  return (
    <div className="stack">
      <PageTitle>Sign in</PageTitle>
      <h1>Sign in</h1>
      <p>Choose a test player. This development sign-in will be replaced by email sign-in.</p>
      {users === 'unavailable' ? (
        <p className="notice notice--error">
          <span className="visually-hidden">Error: </span>
          Sign-in is not available right now. Try again in a few minutes.
        </p>
      ) : (
        <SignInPicker users={users} />
      )}
    </div>
  );
}
