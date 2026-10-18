// P-02 Plan preferences (ST-063b; FR-121; flows-sprint-04 §3): the page shell. The last
// preferences are read in the browser by PlanPreferencesRoute; the API decides access.
import { PageTitle } from '@/components/PageTitle';
import { PlanPreferencesRoute } from '@/components/plan/PlanPreferencesRoute';

export default function PlanPreferencesPage() {
  return (
    <>
      <PageTitle>Your practice setup</PageTitle>
      <PlanPreferencesRoute />
    </>
  );
}
