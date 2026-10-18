'use client';

// Route wrapper for P-02 (ST-063b): reads the last preferences in the browser (no-store), so a
// regenerate visit is prefilled (SC 3.3.7), then shows the form. Signed out → the start page.
// If the last plan cannot be read the form starts empty: the server still checks every answer.
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { PlanPreferences } from './PlanPreferences';
import { createPlanPreferencesApi } from './PlanPreferencesApi';
import type { PlanPreferences as Preferences } from './PlanPreferencesModel';

export function PlanPreferencesRoute() {
  const router = useRouter();
  const api = useMemo(() => createPlanPreferencesApi({ baseUrl: '/api' }), []);
  const [initial, setInitial] = useState<Preferences | null | undefined>(undefined);

  useEffect(() => {
    let live = true;
    void api.lastPreferences().then((read) => {
      if (!live) return;
      if (read.kind === 'signed_out') router.replace('/');
      else setInitial(read.kind === 'preferences' ? read.preferences : null);
    });
    return () => {
      live = false;
    };
  }, [api, router]);

  if (initial === undefined) {
    return <p className="loading" role="status">Loading your setup…</p>;
  }
  return <PlanPreferences initial={initial} api={api} navigate={(path) => router.push(path)} />;
}
