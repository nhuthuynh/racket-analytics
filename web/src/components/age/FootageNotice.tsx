'use client';

// Footage notice (ST-068b; FR-003; flows-sprint-04 §5; PM-4 W-A09): information, not a checkbox;
// it creates no consent. Shown only while the public config says the age gate is on.
import { useEffect, useState } from 'react';
import { browserApi } from '@/lib/api/browser';
import type { ApiClient } from '@/lib/api/client';
import { AGE_WORDING } from '@/lib/identity/age';

export function FootageNotice({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <section className="notice notice--info stack" aria-labelledby="footage-notice">
      <h2 id="footage-notice">Before you upload</h2>
      <p>{AGE_WORDING.footage}</p>
    </section>
  );
}

/** For a static page (F-01): reads the flag in the browser; unreadable config → no notice. */
export function FootageNoticeFromConfig({ api = browserApi }: { api?: Pick<ApiClient, 'publicConfig'> }) {
  const [show, setShow] = useState(false);
  useEffect(() => {
    let live = true;
    api.publicConfig().then(
      ({ ageGate }) => live && setShow(ageGate),
      () => undefined,
    );
    return () => {
      live = false;
    };
  }, [api]);
  return <FootageNotice show={show} />;
}
