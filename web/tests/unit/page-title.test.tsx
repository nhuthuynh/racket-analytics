// Page titles (component checklist §0): "<page> – Racket Analytics", rendered by the page
// itself so the title changes in the same commit as the content (no empty title while
// Next streams metadata during client navigation; found by axe `document-title`).
import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PageTitle, pageTitle } from '@/components/PageTitle';

describe('pageTitle', () => {
  it('rejects an empty page name', () => {
    expect(() => pageTitle('  ')).toThrow();
  });

  it('appends the service name', () => {
    expect(pageTitle('Your matches')).toBe('Your matches – Racket Analytics');
  });
});

describe('PageTitle', () => {
  it('sets the document title', () => {
    render(<PageTitle>New match</PageTitle>);
    expect(document.title).toBe('New match – Racket Analytics');
  });
});
