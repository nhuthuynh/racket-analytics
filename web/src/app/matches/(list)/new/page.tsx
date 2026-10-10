// Match setup Q-01..Q-07 (ST-016). The API decides access (401 → sign-in). The upload caps in
// the Q-06 copy come from GET /upload-policy (flows D-5); if it cannot be read the provisional
// caps are shown and the server still enforces its own.
import { redirect } from 'next/navigation';
import { MatchSetupRoute } from '@/components/MatchSetupRoute';
import { ApiError } from '@/lib/api/client';
import { serverApi } from '@/lib/api/server';
import { FALLBACK_UPLOAD_POLICY, type UploadPolicy } from '@/lib/api/types';

async function loadPolicy(): Promise<UploadPolicy> {
  const api = await serverApi();
  try {
    await api.me();
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) redirect('/');
    throw e;
  }
  try {
    return await api.uploadPolicy();
  } catch {
    return FALLBACK_UPLOAD_POLICY;
  }
}

export default async function NewMatchPage() {
  const policy = await loadPolicy();
  return <MatchSetupRoute policy={policy} />;
}
