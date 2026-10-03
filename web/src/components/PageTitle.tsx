// Page <title> rendered by React 19 (hoisted into <head>). Pages use this instead of
// Next metadata titles: on client navigation Next 15 removes the old metadata title before
// the new one has streamed, leaving the document untitled for ~300 ms (axe document-title,
// serious). A React <title> changes in the same commit as the page content.
export const SERVICE_NAME = 'Racket Analytics';

export function pageTitle(name: string): string {
  if (name.trim().length === 0) throw new Error('page title must not be empty');
  return `${name} – ${SERVICE_NAME}`;
}

export function PageTitle({ children }: { children: string }) {
  return <title>{pageTitle(children)}</title>;
}
