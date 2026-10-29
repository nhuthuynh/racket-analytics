// R-01 Privacy settings (ST-071; flows-sprint-04 §6): exists only while the public config says the
// retention setting or the training choice is on (both off → the app's not-found page). The values
// are read in the browser (no-store), so every state can be shown; the API decides access.
import { notFound } from 'next/navigation';
import { PageTitle } from '@/components/PageTitle';
import { PrivacySettings } from '@/components/settings/PrivacySettings';
import { serverFeatures } from '@/components/settings/PrivacySettingsApi';
import { privacyPageExists, WORDS } from '@/components/settings/PrivacySettingsModel';

export const dynamic = 'force-dynamic';

export default async function PrivacySettingsPage() {
  const features = await serverFeatures();
  if (!privacyPageExists(features)) notFound();
  return (
    <>
      <PageTitle>{WORDS.title}</PageTitle>
      <PrivacySettings features={features} />
    </>
  );
}
