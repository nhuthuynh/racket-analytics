// True once React has hydrated the page; false in the server HTML (NFR-050.8, ST-078e;
// CI-SIGNIN-HYDRATION). Until then a form's onSubmit is not attached, so a tap on its submit
// button would be a native GET submit: the answers in the URL [AQS/SEC-05], nothing handled.
// Forms keep their submit button disabled while this is false (tests/unit/hydration-lock.test.tsx).
import { useSyncExternalStore } from 'react';

const never = () => () => undefined;

export function useHydrated(): boolean {
  return useSyncExternalStore(
    never,
    () => true,
    () => false,
  );
}
