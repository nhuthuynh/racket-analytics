'use client';

// Loading state under /matches (C-30; flows M-01 "skeleton rows with reserved height", never a
// spinner alone). The rows are decoration; the status line says what is loading.
import { usePathname } from 'next/navigation';
import { PageTitle } from '@/components/PageTitle';

export default function Loading() {
  const list = usePathname() === '/matches';
  return (
    <>
      <PageTitle>Loading</PageTitle>
      <p role="status" className="loading">
        {list ? 'Loading your matches…' : 'Loading…'}
      </p>
      <div aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <div key={i} className="skeleton-row" />
        ))}
      </div>
    </>
  );
}
