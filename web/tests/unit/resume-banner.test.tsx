// C-36 (PD-R3-06): several unfinished uploads on M-01 each get a banner with its own name, so a
// screen-reader user can tell the regions apart (SC 2.4.6, 1.3.1).
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ResumeBanner } from '@/components/ResumeBanner';
import type { Match } from '@/lib/api/types';

vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));

const m = (id: string, title: string): Match => ({
  id, title, format: 'singles', status: 'uploading', media: null, created_at: 'x', updated_at: 'x',
  upload: { state: 'receiving', offset: 64, length: 100, expiresAt: '2026-10-06T09:12:44Z', resumeUrl: `/api/uploads/${id}`, fileName: null, fileLastModifiedMs: null, headSha256: null },
});

describe('ResumeBanner', () => {
  it('names each banner after its match', () => {
    render(<ResumeBanner matches={[m('a', 'Sat doubles'), m('b', 'Sun singles')]} />);
    expect(screen.getByRole('region', { name: "Unfinished upload: Sat doubles" })).toBeVisible();
    expect(screen.getByRole('region', { name: "Unfinished upload: Sun singles" })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Resume upload of Sat doubles' })).toBeVisible();
  });
});
