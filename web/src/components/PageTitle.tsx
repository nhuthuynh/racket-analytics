// Page <title> rendered by React 19 (hoisted into <head>). Pages use this instead of
// Next metadata titles: on client navigation Next 15 removes the old metadata title before
// the new one has streamed, leaving the document untitled for ~300 ms (axe document-title,
// serious). A React <title> changes in the same commit as the page content.
export const SERVICE_NAME = 'Racket Analytics';

export function pageTitle(name: string): string {
  if (name.trim().length === 0) throw new Error('page title must not be empty');
  return `${name} – ${SERVICE_NAME}`;
}

/** `error` prefixes "Error: " while an error summary is shown (flows §0, checklist §5). */
export function PageTitle({ children, error = false }: { children: string; error?: boolean }) {
  return <title>{`${error ? 'Error: ' : ''}${pageTitle(children)}`}</title>;
}
