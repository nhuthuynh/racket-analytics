// tus 1.0.0 transport via tus-js-client (ADR 0008; api-sprint-00 §6, §8; AQS/STACK-06).
// Loaded on demand so it is not part of the first route's JavaScript (NFR-015).
import {
  CHUNK_SIZE,
  RETRY_DELAYS,
  shouldRetryUpload,
  uploadEndpointFor,
  uploadFingerprint,
} from './tus-policy';

export interface UploadCallbacks {
  onProgress(bytesSent: number, bytesTotal: number): void;
  onSuccess(): void;
  /** HTTP status of the failing request, 0 when there was no response. */
  onError(status: number): void;
}

export interface UploadHandle {
  abort(): void;
  /** Continue after a failure: tus-js-client asks HEAD for the offset, then PATCHes from it. */
  retry(): void;
}

export type StartUpload = (file: File, matchId: string, callbacks: UploadCallbacks) => UploadHandle;

export const startTusUpload: StartUpload = (file, matchId, callbacks) => {
  const endpoint = uploadEndpointFor(matchId);
  let upload: import('tus-js-client').Upload | null = null;
  let aborted = false;

  void import('tus-js-client').then(async ({ Upload }) => {
    if (aborted) return;
    const fingerprint = uploadFingerprint(file, matchId);
    upload = new Upload(file, {
      endpoint,
      chunkSize: CHUNK_SIZE,
      retryDelays: RETRY_DELAYS,
      // No metadata: the server stores none in Sprint 0, and the file name may be personal
      // data (api-sprint-00 §6.2, data minimisation).
      metadata: {},
      fingerprint: async () => fingerprint,
      storeFingerprintForResuming: true,
      removeFingerprintOnSuccess: true,
      onProgress: (sent, total) => callbacks.onProgress(sent, total),
      onSuccess: () => callbacks.onSuccess(),
      onError: (error) => {
        const response = (error as { originalResponse?: { getStatus(): number } | null })
          .originalResponse;
        callbacks.onError(response ? response.getStatus() : 0);
      },
      onShouldRetry: (error) =>
        shouldRetryUpload({
          method: error.originalRequest?.getMethod() ?? 'PATCH',
          status: error.originalResponse?.getStatus() ?? 0,
          online: typeof navigator === 'undefined' ? true : navigator.onLine,
        }),
    });
    const previous = await upload.findPreviousUploads();
    const [latest] = previous.sort((a, b) => b.creationTime.localeCompare(a.creationTime));
    if (latest) upload.resumeFromPreviousUpload(latest);
    if (!aborted) upload.start();
  });

  return {
    abort() {
      aborted = true;
      void upload?.abort();
    },
    retry() {
      upload?.start();
    },
  };
};
