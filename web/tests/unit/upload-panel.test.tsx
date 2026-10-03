// Upload panel: file picker (no drag required, SC 2.5.7) wired to a tus upload. The tus
// transport is replaced by a fake here; the real one runs in the walking-skeleton E2E.
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { UploadPanel } from '@/components/UploadPanel';
import type { StartUpload, UploadCallbacks } from '@/lib/upload/tus-upload';

const MATCH_ID = '0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10';
const clip = () => new File([new Uint8Array(2_000)], 'clip.mp4', { type: 'video/mp4' });

function fakeTransport() {
  let callbacks: UploadCallbacks | null = null;
  const abort = vi.fn();
  const retry = vi.fn();
  const start = vi.fn<StartUpload>((_file, _matchId, cb) => {
    callbacks = cb;
    return { abort, retry };
  });
  return { start, abort, retry, cb: () => callbacks! };
}

describe('UploadPanel', () => {
  it('does not start anything until a file is chosen', () => {
    const t = fakeTransport();
    render(<UploadPanel matchId={MATCH_ID} startUpload={t.start} onUploaded={vi.fn()} />);
    expect(screen.getByLabelText(/match video/i)).toHaveAttribute('type', 'file');
    expect(screen.queryByRole('progressbar')).toBeNull();
    expect(t.start).not.toHaveBeenCalled();
  });

  it('ignores a non-video file and says why', async () => {
    const t = fakeTransport();
    render(<UploadPanel matchId={MATCH_ID} startUpload={t.start} onUploaded={vi.fn()} />);
    const input = screen.getByLabelText(/match video/i);
    await userEvent.upload(input, new File(['x'], 'notes.txt', { type: 'text/plain' }), {
      applyAccept: false,
    });
    expect(screen.getByText(/choose a video file/i)).toBeVisible();
    expect(t.start).not.toHaveBeenCalled();
  });

  it('starts the upload on file choice and shows progress', async () => {
    const t = fakeTransport();
    render(<UploadPanel matchId={MATCH_ID} startUpload={t.start} onUploaded={vi.fn()} />);
    await userEvent.upload(screen.getByLabelText(/match video/i), clip());
    expect(t.start).toHaveBeenCalledWith(expect.any(File), MATCH_ID, expect.any(Object));
    expect(screen.getByRole('progressbar', { name: /upload/i })).toHaveAttribute(
      'aria-valuenow',
      '0',
    );

    act(() => t.cb().onProgress(1_000, 2_000));
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '50');
    act(() => t.cb().onProgress(500, 2_000)); // regression ignored
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '50');
  });

  it('reports completion and announces it politely', async () => {
    const t = fakeTransport();
    const onUploaded = vi.fn();
    render(<UploadPanel matchId={MATCH_ID} startUpload={t.start} onUploaded={onUploaded} />);
    await userEvent.upload(screen.getByLabelText(/match video/i), clip());
    act(() => t.cb().onSuccess());
    expect(onUploaded).toHaveBeenCalledOnce();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
    expect(screen.getByTestId('upload-announcer')).toHaveTextContent('Upload complete');
  });

  it('shows a failure and retries from where it stopped', async () => {
    const t = fakeTransport();
    render(<UploadPanel matchId={MATCH_ID} startUpload={t.start} onUploaded={vi.fn()} />);
    await userEvent.upload(screen.getByLabelText(/match video/i), clip());
    act(() => t.cb().onProgress(800, 2_000));
    act(() => t.cb().onError(0));
    expect(screen.getByText(/upload stopped/i)).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: 'Try the upload again' }));
    expect(t.retry).toHaveBeenCalledOnce();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '40');
  });

  it('asks for the same file again when the server already has an upload', () => {
    const t = fakeTransport();
    render(
      <UploadPanel matchId={MATCH_ID} startUpload={t.start} onUploaded={vi.fn()} resuming />,
    );
    expect(screen.getByText(/choose the same video file/i)).toBeVisible();
  });

  it('aborts the transport when the panel goes away', async () => {
    const t = fakeTransport();
    const { unmount } = render(
      <UploadPanel matchId={MATCH_ID} startUpload={t.start} onUploaded={vi.fn()} />,
    );
    await userEvent.upload(screen.getByLabelText(/match video/i), clip());
    unmount();
    expect(t.abort).toHaveBeenCalled();
  });
});
