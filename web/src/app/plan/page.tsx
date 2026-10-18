// P-01 Your training plan (ST-063a; flows-sprint-04 §2). The page shell; the plan is read in the
// browser by PlanView (no-store), so every visit is current and the states can be shown. An
// unknown sub-route (/plan/<anything> but /plan/new, ST-063b) is the app's not-found page.
import { PageTitle } from '@/components/PageTitle';
import { PlanView } from '@/components/plan/PlanView';

export default function PlanPage() {
  return (
    <div className="stack">
      <PageTitle>Your training plan</PageTitle>
      <h1 tabIndex={-1}>Your training plan</h1>
      <PlanView />
    </div>
  );
}
