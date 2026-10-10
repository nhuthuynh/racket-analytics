'use client';

// M-01 after a deletion (ST-050; flows-sprint-03 §4 "After 202"): a polite notice that does not
// name the match (the list shows no trace of it), and focus on the page's <h1>.
import { useEffect } from 'react';

const NOTICES: Readonly<Record<string, string>> = {
  '1': 'The match was deleted. Its stored files are removed within 7 days.',
  already: 'This match was already deleted.',
};

export function DeletedNotice({ which }: { which: string | undefined }) {
  const text = which ? NOTICES[which] : undefined;
  useEffect(() => {
    if (text) document.querySelector<HTMLElement>('h1')?.focus();
  }, [text]);
  if (!text) return null;
  return (
    <p role="status" className="notice notice--info">
      {text}
    </p>
  );
}
