// Upload panel U-01..U-04 (ST-017, ST-018; flows §6; FR-022, FR-023). The tus transfer is a
// fake here; the protocol runs for real in E2E-01-02 and the upload-validation spec.
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MatchUpload } from '@/components/MatchUpload';
import { FALLBACK_UPLOAD_POLICY, type Match, type UploadState } from '@/lib/api/types';
import { getActiveUpload, setActiveUpload } from '@/lib/upload/activity';
import { headSha256Hex } from '@/lib/upload/digest';
import type { StartTransfer, TransferCallbacks, TransferOptions } from '@/lib/upload/transfer';

const ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const RESUME = '/api/uploads/5d0c6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const match: Match = {
  id: ID, title: 'Singles · 5 Oct 2026', format: 'singles', status: 'awaiting_upload', media: null,
  created_at: 'x', updated_at: 'x', participants: [], upload: null, rejection: null,
};
const video = (size = 1000, name = 'Sat doubles.mp4') =>
  new File([new Uint8Array(size).fill(3)], name, { type: 'video/mp4', lastModified: 1759480000000 });

afterEach(() => setActiveUpload(null));

function fakeTransfer() {
  let options: TransferOptions | null = null;
  const handle = { pause: vi.fn(), resume: vi.fn(), abort: vi.fn() };
  const start = vi.fn<StartTransfer>((o) => {
    options = o;
    return handle;
  });
  return { start, handle, cb: (): TransferCallbacks => options!.callbacks, options: () => options! };
}

function renderPanel(props: Partial<Parameters<typeof MatchUpload>[0]> = {}) {
  const t = fakeTransfer();
  const onUploaded = vi.fn();
  render(
    <MatchUpload
      match={match}
      policy={FALLBACK_UPLOAD_POLICY}
      startTransfer={t.start}
      onUploaded={onUploaded}
      onProblem={vi.fn()}
      {...props}
    />,
  );
  return { t, onUploaded };
}

describe('MatchUpload', () => {
  it('shows "No video yet" with a file button and starts nothing until a file is chosen', () => {
    const { t } = renderPanel();
    expect(screen.getByRole('heading', { name: 'Video upload' })).toBeVisible();
    expect(screen.getByText('No video yet')).toBeVisible();
    expect(screen.getByLabelText('Choose video')).toHaveAttribute('type', 'file');
    expect(t.start).not.toHaveBeenCalled();
  });

  it('starts at once with the file handed over from setup, with honest progress and no estimate yet', () => {
    const { t } = renderPanel({ initialFile: video(1_724_207) });
    expect(t.start).toHaveBeenCalledOnce();
    expect(t.options().matchId).toBe(ID);
    act(() => t.cb().onProgress(1_100_000, 1_724_207));
    expect(screen.getByText('63% · 1.1 MB of 1.7 MB')).toBeVisible();
    expect(screen.getByText('Uploading', { exact: true })).toBeVisible();
    expect(screen.queryByText(/left$/)).toBeNull();
    expect(screen.getByText(/If you close it, you can resume later from this page by choosing the same video\./)).toBeVisible();
    expect(screen.getByText('Only you can see this video.')).toBeVisible();
  });

  it('pauses while offline and resumes from the server offset when the connection returns', () => {
    const { t } = renderPanel({ initialFile: video() });
    act(() => {
      window.dispatchEvent(new Event('offline'));
    });
    expect(screen.getByText('Paused: waiting for connection')).toBeVisible();
    expect(t.handle.pause).toHaveBeenCalled();
    act(() => {
      window.dispatchEvent(new Event('online'));
    });
    expect(screen.getByText('Resuming')).toBeVisible();
    expect(t.handle.resume).toHaveBeenCalled();
    act(() => t.cb().onProgress(500, 1000));
    expect(screen.getByText('Uploading', { exact: true })).toBeVisible();
  });

  it('says it is having trouble after 3 retries in a row, invisibly retrying before that', () => {
    const { t } = renderPanel({ initialFile: video() });
    act(() => t.cb().onRetrying!(460));
    act(() => t.cb().onRetrying!(460));
    expect(screen.getByText('Uploading', { exact: true })).toBeVisible();
    act(() => t.cb().onRetrying!(460));
    expect(screen.getByText("Paused: we're having trouble sending your video. Retrying…")).toBeVisible();
  });

  it('U-03: a file refused by content shows the error summary and saves nothing', async () => {
    const onProblem = vi.fn();
    const { t } = renderPanel({ initialFile: video(), onProblem });
    act(() => t.cb().onError(415));
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('There is a problem');
    expect(screen.getByRole('link', { name: 'This file is not a video we can read' })).toBeVisible();
    expect(screen.getByText('Nothing from this file was saved.')).toBeVisible();
    await userEvent.click(screen.getByRole('link', { name: 'Choose a different video' }));
    expect(screen.getByLabelText('Choose video')).toHaveFocus();
    expect(onProblem).toHaveBeenCalledWith(true);
  });

  it('U-03: refuses a file above the size cap before sending anything', async () => {
    const { t } = renderPanel({ policy: { ...FALLBACK_UPLOAD_POLICY, maxBytes: 500_000 } });
    await userEvent.upload(screen.getByLabelText('Choose video'), video(600_000));
    expect(screen.getByRole('link', { name: 'Videos must be 500 KB or smaller' })).toBeVisible();
    expect(t.start).not.toHaveBeenCalled();
  });

  it('shows the server rejection of the last file (probe: too long)', () => {
    renderPanel({ match: { ...match, rejection: { code: 'too_long', at: 'x' } } });
    expect(screen.getByRole('link', { name: 'Videos must be 2 hours 30 minutes or shorter' })).toBeVisible();
    expect(screen.getByText('No video yet')).toBeVisible();
  });

  it('PD-R2-02: an unfinished-upload quota refusal shows no progress and links to Your matches', () => {
    const { t } = renderPanel({ initialFile: video(1_724_207) });
    act(() => t.cb().onError(429));
    expect(screen.queryByRole('progressbar')).toBeNull();
    expect(screen.queryByText('Stopped')).toBeNull();
    expect(screen.queryByText(/You can use other pages while this tab stays open/)).toBeNull();
    expect(screen.getByRole('alert')).toHaveFocus();
    const link = screen.getByRole('link', { name: /too many unfinished uploads/ });
    expect(link).toHaveAttribute('href', '/matches');
    expect(screen.queryByText('Nothing from this file was saved.')).toBeNull();
    expect(screen.getByText('No video yet')).toBeVisible();
  });

  it('PD-R2-02: a conflict refusal before any byte was sent shows no progress', () => {
    const { t } = renderPanel({ initialFile: video(1_724_207) });
    act(() => t.cb().onError(409));
    expect(screen.queryByRole('progressbar')).toBeNull();
    expect(screen.queryByText('Stopped')).toBeNull();
    expect(screen.getByRole('link', { name: /already has an unfinished upload/ })).toBeVisible();
  });

  it('PD-R2-02: a failure after bytes were sent keeps the progress it made', () => {
    const { t } = renderPanel({ initialFile: video(1000) });
    act(() => t.cb().onProgress(640, 1000));
    act(() => t.cb().onError(500));
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '64');
    expect(screen.getByText('Stopped')).toBeVisible();
  });

  // PD-R3-03: tus-js-client reports bytes SENT while a PATCH is in flight, also when the server
  // then answers 500. Only an accepted chunk proves progress, so "trouble" shows after 3 failed
  // retries even though every retry sent bytes again (flows §6 U-01).
  it('PD-R3-03: says it is having trouble when PATCHes keep failing after sending bytes', () => {
    const { t } = renderPanel({ initialFile: video(1000) });
    for (let i = 0; i < 3; i += 1) {
      act(() => t.cb().onProgress(0, 1000));
      act(() => t.cb().onProgress(1000, 1000));
      act(() => t.cb().onRetrying!(500));
    }
    expect(screen.getByText("Paused: we're having trouble sending your video. Retrying…")).toBeVisible();
  });

  it('PD-R3-03: an accepted chunk ends the trouble state and starts the retry count again', () => {
    const { t } = renderPanel({ initialFile: video(1000) });
    for (let i = 0; i < 3; i += 1) act(() => t.cb().onRetrying!(500));
    expect(screen.getByText(/having trouble/)).toBeVisible();
    act(() => t.cb().onChunkAccepted!(500));
    act(() => t.cb().onProgress(600, 1000));
    expect(screen.getByText('Uploading', { exact: true })).toBeVisible();
    act(() => t.cb().onRetrying!(500));
    expect(screen.getByText('Uploading', { exact: true })).toBeVisible();
  });

  it('PD-R3-03: does not say progress is saved when the server kept nothing', () => {
    const { t } = renderPanel({ initialFile: video(1000) });
    act(() => t.cb().onProgress(1000, 1000));
    act(() => t.cb().onError(500));
    expect(screen.getByText('Stopped')).toBeVisible();
    expect(screen.queryByText(/Your progress is saved/)).toBeNull();
    expect(screen.getByRole('link', { name: /problem on our side/ })).toBeVisible();
  });

  it('PD-R3-03: says progress is saved when the server kept part of the video', () => {
    const { t } = renderPanel({ initialFile: video(1000) });
    act(() => t.cb().onChunkAccepted!(500));
    act(() => t.cb().onProgress(500, 1000));
    act(() => t.cb().onError(500));
    expect(screen.getByRole('link', { name: /Your progress is saved\. Try again\./ })).toBeVisible();
  });

  it('PE-R3-03 / PD-R3-02: a creation-rate limit is not called a quota and gives the time to try again', () => {
    const { t } = renderPanel({ initialFile: video(1000) });
    act(() => t.cb().onError(429, { code: 'rate_limited', retryAt: '2026-10-05T14:32:00Z', supportRef: null }));
    expect(screen.queryByText(/too many unfinished uploads/)).toBeNull();
    const link = screen.getByRole('link', { name: /^You have started too many uploads in a short time\. You can try again at \d{2}:\d{2}\.$/ });
    expect(link).toHaveAttribute('href', '#video-file');
    expect(screen.queryByRole('progressbar')).toBeNull();
    expect(screen.getByRole('alert')).toHaveFocus();
    expect(screen.getByLabelText('Choose video')).toBeInTheDocument();
  });

  it('reports completion and then checks the video', () => {
    const { t, onUploaded } = renderPanel({ initialFile: video() });
    act(() => t.cb().onSuccess());
    expect(screen.getByText('Checking video…')).toBeVisible();
    expect(onUploaded).toHaveBeenCalledOnce();
  });

  it('tells sign-out about the running upload, and forgets it when done', () => {
    const { t } = renderPanel({ initialFile: video() });
    act(() => t.cb().onProgress(640, 1000));
    expect(getActiveUpload()).toMatchObject({ title: 'Singles · 5 Oct 2026', percent: 64 });
    act(() => t.cb().onSuccess());
    expect(getActiveUpload()).toBeNull();
  });
});

describe('MatchUpload, resume on return (U-04)', () => {
  async function receiving(over: Partial<UploadState> = {}): Promise<Match> {
    return {
      ...match,
      status: 'uploading',
      upload: {
        state: 'receiving', offset: 640, length: 1000, expiresAt: '2026-10-06T09:12:44Z', resumeUrl: RESUME,
        fileName: 'Sat doubles.mp4', fileLastModifiedMs: 1759480000000, headSha256: await headSha256Hex(video()),
        ...over,
      },
    };
  }

  it('asks for the same video and refuses a different one, keeping the upload as it was', async () => {
    const { t } = renderPanel({ match: await receiving() });
    expect(screen.getByText(/To continue, choose the same video:/)).toHaveTextContent('Sat doubles.mp4 (1.0 KB)');
    await userEvent.upload(screen.getByLabelText('Choose video'), video(1000, 'clip.mp4'));
    expect(await screen.findByRole('link', { name: /This is not the same video/ })).toBeVisible();
    expect(t.start).not.toHaveBeenCalled();
  });

  it('PD-R3-01: choosing a different video again moves focus back to the error summary', async () => {
    renderPanel({ match: await receiving() });
    await userEvent.upload(screen.getByLabelText('Choose video'), video(1000, 'clip.mp4'));
    const first = await screen.findByRole('alert');
    await vi.waitFor(() => expect(first).toHaveFocus());
    await userEvent.upload(screen.getByLabelText('Choose video'), video(1000, 'clip.mp4'));
    expect(screen.getByLabelText('Choose video')).not.toHaveFocus();
    await vi.waitFor(() => expect(screen.getByRole('alert')).toHaveFocus());
  });

  it('continues the server upload with the same video', async () => {
    const { t } = renderPanel({ match: await receiving() });
    await userEvent.upload(screen.getByLabelText('Choose video'), video());
    await vi.waitFor(() => expect(t.start).toHaveBeenCalledOnce());
    expect(t.options().resumeUrl).toBe(RESUME);
    expect(t.options().matchId).toBeUndefined();
  });

  it('says an expired upload must start again, and starts a new one', async () => {
    const { t } = renderPanel({ match: await receiving({ state: 'expired' }) });
    expect(screen.getByText(/^This upload expired on .+\. Start the upload again\.$/)).toBeVisible();
    await userEvent.upload(screen.getByLabelText('Choose video'), video());
    expect(t.options().matchId).toBe(ID);
  });
});

// C-03 (PD-R3V-01, major) with C-35 (PD-R3-04): after a server error the panel offers recovery
// per flows-sprint-01 §6 "Upload states summary": "Try again" keeps the transfer (resumes from the
// server offset, no new upload), no contradictory "No video yet", and the support_ref is shown.
describe('MatchUpload, recovery after a server error (C-03, C-35)', () => {
  const REF = 'ref_0123456789abcdef';

  it('C-03: does not show "No video yet" or the file chooser while a stopped transfer can continue', () => {
    const { t } = renderPanel({ initialFile: video(1000) });
    act(() => t.cb().onChunkAccepted!(400));
    act(() => t.cb().onProgress(400, 1000));
    act(() => t.cb().onError(500, { code: 'internal_error', retryAt: null, supportRef: REF }));
    expect(screen.queryByText('No video yet')).toBeNull();
    expect(screen.queryByLabelText('Choose video')).toBeNull();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '40');
  });

  it('C-03 / C-35: shows the flows §6 server-error copy with the support reference, and a "Try again" button', () => {
    const { t } = renderPanel({ initialFile: video(1000) });
    act(() => t.cb().onChunkAccepted!(400));
    act(() => t.cb().onProgress(400, 1000));
    act(() => t.cb().onError(500, { code: 'internal_error', retryAt: null, supportRef: REF }));
    const link = screen.getByRole('link', {
      name: `Sorry, the upload stopped because of a problem on our side. Your progress is saved. Try again. Reference: ${REF}`,
    });
    expect(link).toHaveAttribute('href', '#upload-try-again');
    expect(screen.getByRole('button', { name: 'Try again' })).toBeVisible();
  });

  it('C-03: the summary link moves focus to "Try again"', async () => {
    const { t } = renderPanel({ initialFile: video(1000) });
    act(() => t.cb().onError(503));
    await userEvent.click(screen.getByRole('link', { name: /problem on our side/ }));
    expect(screen.getByRole('button', { name: 'Try again' })).toHaveFocus();
  });

  it('C-03: "Try again" continues the same transfer from the server offset, never a new upload', async () => {
    const { t } = renderPanel({ initialFile: video(1000) });
    act(() => t.cb().onChunkAccepted!(400));
    act(() => t.cb().onProgress(400, 1000));
    act(() => t.cb().onError(500, { code: 'internal_error', retryAt: null, supportRef: REF }));
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(t.handle.resume).toHaveBeenCalledOnce();
    expect(t.start).toHaveBeenCalledOnce();
    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.getByText('Resuming')).toBeVisible();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '40');
    act(() => t.cb().onProgress(700, 1000));
    expect(screen.getByText('Uploading', { exact: true })).toBeVisible();
    act(() => t.cb().onSuccess());
    expect(screen.getByText('Checking video…')).toBeVisible();
  });

  it('C-03: a second failure after "Try again" offers "Try again" again and moves focus to the summary', async () => {
    const { t } = renderPanel({ initialFile: video(1000) });
    act(() => t.cb().onError(500));
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    act(() => t.cb().onError(500));
    expect(screen.getByRole('button', { name: 'Try again' })).toBeVisible();
    await vi.waitFor(() => expect(screen.getByRole('alert')).toHaveFocus());
  });

  it('C-03: a dropped connection while online also offers "Try again" and keeps the transfer', async () => {
    const { t } = renderPanel({ initialFile: video(1000) });
    act(() => t.cb().onError(0));
    expect(screen.getByRole('link', { name: /Check your connection, then try again/ })).toBeVisible();
    expect(screen.queryByText('No video yet')).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(t.handle.resume).toHaveBeenCalledOnce();
  });

  it('C-03: refusals that cannot be retried still end the transfer and show the chooser (expired)', () => {
    const { t } = renderPanel({ initialFile: video(1000) });
    act(() => t.cb().onProgress(400, 1000));
    act(() => t.cb().onError(410));
    expect(screen.queryByRole('button', { name: 'Try again' })).toBeNull();
    expect(screen.getByLabelText('Choose video')).toBeInTheDocument();
  });
});
