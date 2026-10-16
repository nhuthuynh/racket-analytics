'use client';

// X-01 Delete this match? (ST-050; FR-006, NFR-066; flows-sprint-03 §4). The last section of M-02,
// away from "Tag rallies" and "Stats". The dialog lists what goes, that it cannot be undone and
// the 7-day purge; only its button sends `{"confirm": "delete"}` (api-sprint-03 §4.1). After 202
// the player lands on M-01 with a notice that does not repeat the title.
import { useEffect, useRef, useState } from 'react';
import { formatLocalDate } from '@/components/LocalDate';
import { ApiError, type ApiClient } from '@/lib/api/client';
import { browserApi } from '@/lib/api/browser';
import type { Match } from '@/lib/api/types';
import { getActiveUpload } from '@/lib/upload/activity';
import { ConfirmDialog } from './ConfirmDialog';

function go(path: string) {
  window.location.assign(path);
}

export function deleteProblem(e: unknown, what: string): string {
  if (e instanceof ApiError && e.code === 'network_error') return `${what} was not deleted because the connection dropped. Try again.`;
  const ref = e instanceof ApiError && e.supportRef ? ` Reference: ${e.supportRef}` : '';
  return `${what} was not deleted. Try again.${ref}`;
}

// The server's default title is "{Doubles|Singles} · {d Mon yyyy}" (flows D-2), its months always
// three letters; Intl en-GB writes September as "Sept". A title that already ends with the date
// played is shown alone, so the dialog never says the date twice (MVP-04).
const SERVER_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function matchSummary(title: string, iso: string): string {
  const date = formatLocalDate(iso, 'UTC');
  if (!date) return title;
  const d = new Date(iso);
  const serverDate = `${d.getUTCDate()} ${SERVER_MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  if (title.endsWith(date) || title.endsWith(serverDate)) return title;
  return `${title} · ${date}`;
}

export function DeleteMatch({
  match,
  api = browserApi,
  navigate = go,
}: {
  match: Match;
  api?: Pick<ApiClient, 'deleteMatch'>;
  navigate?: (path: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const opener = useRef<HTMLButtonElement>(null);
  const uploading = match.status === 'uploading' || getActiveUpload() !== null;
  const summary = matchSummary(match.title, match.played_on ?? match.created_at);

  // When the dialog has gone (Cancel or Esc), focus returns to the button that opened it.
  const wasOpen = useRef(false);
  useEffect(() => {
    if (!open && wasOpen.current) opener.current?.focus();
    wasOpen.current = open;
  }, [open]);

  function close() {
    setOpen(false);
  }

  async function confirm(): Promise<string | null> {
    try {
      await api.deleteMatch(match.id);
      getActiveUpload()?.stop();
      navigate('/matches?deleted=1');
      return null;
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        navigate('/matches?deleted=already');
        return null;
      }
      if (e instanceof ApiError && e.status === 401) {
        navigate('/');
        return null;
      }
      return deleteProblem(e, 'The match');
    }
  }

  return (
    <section className="stack delete-section" aria-labelledby="delete-match-title">
      <h2 id="delete-match-title">Delete this match</h2>
      <p>Deleting removes the video and everything made from it.</p>
      <p>
        <button ref={opener} type="button" className="button button--danger" onClick={() => setOpen(true)}>
          Delete match
        </button>
      </p>
      {open ? (
        <ConfirmDialog
          id="delete-match-dialog"
          title="Delete this match?"
          confirmLabel="Delete match"
          busyLabel="Deleting…"
          onConfirm={confirm}
          onCancel={close}
        >
          <p>{summary}</p>
          <ul className="consequences">
            <li>This deletes the video, tags, score sheet and stats of this match.</li>
            <li>It cannot be undone.</li>
            <li>The match leaves your account at once. Its stored files are removed within 7 days.</li>
            {uploading ? <li>The upload in progress stops.</li> : null}
          </ul>
        </ConfirmDialog>
      ) : null}
    </section>
  );
}
