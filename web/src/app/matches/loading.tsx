import { PageTitle } from '@/components/PageTitle';

export default function Loading() {
  return (
    <>
      <PageTitle>Loading</PageTitle>
      <p role="status" className="loading">
        Loading…
      </p>
    </>
  );
}
