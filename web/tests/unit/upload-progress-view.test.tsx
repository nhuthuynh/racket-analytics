// Upload progress view, component checklist §6: progressbar with valuenow/min/max/valuetext,
// % and MB visible as text (FR-022), never more than 100%.
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { UploadProgressView } from '@/components/UploadProgressView';
import type { UploadProgress } from '@/lib/upload/progress';

const state = (overrides: Partial<UploadProgress>): UploadProgress => ({
  phase: 'uploading',
  bytesSent: 0,
  bytesTotal: 1_724_207,
  failure: null,
  ...overrides,
});

describe('UploadProgressView', () => {
  it('renders nothing before an upload starts', () => {
    const { container } = render(
      <UploadProgressView progress={state({ phase: 'idle', bytesTotal: 0 })} onRetry={vi.fn()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('exposes an accessible progressbar named for the upload', () => {
    render(<UploadProgressView progress={state({ bytesSent: 1_100_000 })} onRetry={vi.fn()} />);
    const bar = screen.getByRole('progressbar', { name: /upload/i });
    expect(bar).toHaveAttribute('aria-valuenow', '63');
    expect(bar).toHaveAttribute('aria-valuemin', '0');
    expect(bar).toHaveAttribute('aria-valuemax', '100');
    expect(bar).toHaveAttribute('aria-valuetext', '63%, 1.1 of 1.7 MB');
  });

  it('shows the percentage and MB as text, not only as a bar', () => {
    render(<UploadProgressView progress={state({ bytesSent: 1_100_000 })} onRetry={vi.fn()} />);
    expect(screen.getByText('63% · 1.1 of 1.7 MB')).toBeVisible();
  });

  it('shows 100% when complete', () => {
    render(
      <UploadProgressView
        progress={state({ phase: 'complete', bytesSent: 1_724_207 })}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
    expect(screen.getByText('Upload complete')).toBeVisible();
  });

  it('explains a failure in words and offers a retry', async () => {
    const onRetry = vi.fn();
    render(
      <UploadProgressView
        progress={state({ phase: 'failed', bytesSent: 500_000, failure: 'network' })}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText(/upload stopped/i)).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: 'Try the upload again' }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('does not offer a retry when the server refused the upload', () => {
    render(
      <UploadProgressView
        progress={state({ phase: 'failed', bytesSent: 0, failure: 'conflict' })}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText(/already has an upload/i)).toBeVisible();
    expect(screen.queryByRole('button')).toBeNull();
  });
});
