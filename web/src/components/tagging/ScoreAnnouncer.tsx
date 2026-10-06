// One polite live region for score announcements (ST-029; FR-048; DES FR-UX-62). It is rendered
// from the first paint and only its text changes, so screen readers announce each new message
// without focus moving (SC 4.1.3). It is also the visible "last rally" line, so sighted and
// screen-reader users get the same words. The call format is provisional (@needs-verification).
export function ScoreAnnouncer({ message }: { message: string }) {
  return (
    <p className="quick-tag__last" role="status" aria-live="polite" aria-atomic="true">
      {message}
    </p>
  );
}
