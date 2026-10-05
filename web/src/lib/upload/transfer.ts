// tus 1.0.0 transfer, Sprint 1 (ST-017; api-sprint-01 §6.3-§6.5; ADR 0011; AQS/STACK-06).
// - Creation sends `filename`, `last_modified` and `head_sha256` metadata so a later visit can
//   check "the same video" (flows U-04). The file name stays on the server only.
// - Every PATCH carries `Upload-Checksum: sha256 <base64>` (checksum extension); a damaged
//   chunk (460) is retried from the server's offset.
// - Resume uses the server's `resume_url` and no endpoint, so an expired upload (410) is
//   reported, never silently replaced by a new one.
// - No upload URL is stored on the device: server state is the resume source (flows D-3).
// - The chunk size adapts to the measured rate within the policy bounds (NFR-016).
// tus-js-client is loaded on demand, outside the first route's JavaScript (NFR-015).
import type { HttpRequest, HttpStack } from 'tus-js-client';
import { isPublicId } from '@/lib/api/types';
import { headSha256Hex, sha256Base64 } from './digest';
import {
  nextChunkSize,
  RETRY_DELAYS,
  shouldRetryUpload,
  uploadEndpointFor,
  uploadErrorDetail,
  type UploadErrorDetail,
} from './tus-policy';

const RESUME_URL_RE = /^\/api\/uploads\/([0-9a-f-]{36})$/;

export interface TransferCallbacks {
  onProgress(bytesSent: number, bytesTotal: number): void;
  onSuccess(): void;
  /**
   * Final failure: HTTP status of the failing request, 0 when there was no response, plus the
   * API error envelope when the response carried one (e.g. 429 `rate_limited` + `retry_at`).
   */
  onError(status: number, detail?: UploadErrorDetail): void;
  /** A retry was scheduled after this status (0 = no response). */
  onRetrying?(status: number): void;
  /**
   * The server accepted a chunk: the stored offset is now `bytesAccepted`. Unlike onProgress
   * (bytes sent, also for a PATCH the server then refuses), this proves progress (PD-R3-03).
   */
  onChunkAccepted?(bytesAccepted: number): void;
}

export interface TransferHandle {
  pause(): void;
  resume(): void;
  abort(): void;
}

export interface TransferOptions {
  file: File;
  /** New upload for this match… */
  matchId?: string;
  /** …or continue the server's unfinished upload. */
  resumeUrl?: string;
  policy: { chunkMinBytes: number; chunkMaxBytes: number };
  callbacks: TransferCallbacks;
}

export type StartTransfer = (options: TransferOptions) => TransferHandle;

/** Adds the checksum header to PATCH requests, computed from the exact body sent. */
function checksumStack(inner: HttpStack): HttpStack {
  return {
    createRequest(method: string, url: string): HttpRequest {
      const request = inner.createRequest(method, url);
      if (method.toUpperCase() !== 'PATCH') return request;
      const send = request.send.bind(request);
      request.send = async (body?: unknown) => {
        if (body instanceof Blob && body.size > 0) {
          request.setHeader('Upload-Checksum', `sha256 ${await sha256Base64(body)}`);
        }
        return send(body as never);
      };
      return request;
    },
    getName: () => 'ChecksumHttpStack',
  };
}

type FailedResponse = { getStatus(): number; getBody?(): string } | null | undefined;

function statusOf(error: unknown): number {
  const response = (error as { originalResponse?: FailedResponse }).originalResponse;
  return response ? response.getStatus() : 0;
}

/** The error envelope of the failing response, or undefined when it said nothing usable. */
function detailOf(error: unknown): UploadErrorDetail | undefined {
  const response = (error as { originalResponse?: FailedResponse }).originalResponse;
  if (!response?.getBody) return undefined;
  const detail = uploadErrorDetail(response.getBody());
  return detail.code || detail.retryAt || detail.supportRef ? detail : undefined;
}

export const startTransfer: StartTransfer = ({ file, matchId, resumeUrl, policy, callbacks }) => {
  if (resumeUrl !== undefined) {
    const id = RESUME_URL_RE.exec(resumeUrl)?.[1];
    if (!id || !isPublicId(id)) throw new Error('not an upload URL');
  }
  const endpoint = resumeUrl === undefined ? uploadEndpointFor(matchId ?? '') : undefined;
  const bounds = { min: policy.chunkMinBytes, max: Math.max(policy.chunkMinBytes, policy.chunkMaxBytes) };
  let upload: import('tus-js-client').Upload | null = null;
  let stopped = false;
  let chunkStartedAt = 0;

  void (async () => {
    const [{ Upload, DefaultHttpStack }, head] = await Promise.all([
      import('tus-js-client'),
      endpoint ? headSha256Hex(file) : Promise.resolve(null),
    ]);
    if (stopped) return;
    upload = new Upload(file, {
      ...(endpoint ? { endpoint } : { uploadUrl: resumeUrl }),
      chunkSize: bounds.min,
      retryDelays: RETRY_DELAYS,
      metadata: head
        ? { filename: file.name, last_modified: String(file.lastModified), head_sha256: head }
        : {},
      storeFingerprintForResuming: false,
      httpStack: checksumStack(new DefaultHttpStack({})),
      onBeforeRequest: (req) => {
        if (req.getMethod() === 'PATCH') chunkStartedAt = performance.now();
      },
      onChunkComplete: (chunkSize, bytesAccepted) => {
        callbacks.onChunkAccepted?.(bytesAccepted);
        if (!upload) return;
        const ms = chunkStartedAt > 0 ? performance.now() - chunkStartedAt : 0;
        upload.options.chunkSize = nextChunkSize(chunkSize, ms, bounds);
      },
      onProgress: (sent, total) => callbacks.onProgress(sent, total),
      onSuccess: () => callbacks.onSuccess(),
      onError: (error) => {
        const detail = detailOf(error);
        if (detail) callbacks.onError(statusOf(error), detail);
        else callbacks.onError(statusOf(error));
      },
      onShouldRetry: (error) => {
        const status = statusOf(error);
        const retry = shouldRetryUpload({
          method: error.originalRequest?.getMethod() ?? 'PATCH',
          status,
          online: typeof navigator === 'undefined' ? true : navigator.onLine,
        });
        if (retry) callbacks.onRetrying?.(status);
        return retry;
      },
    });
    upload.start();
  })();

  return {
    pause() {
      void upload?.abort(false);
    },
    resume() {
      upload?.start();
    },
    abort() {
      stopped = true;
      void upload?.abort(false);
    },
  };
};
