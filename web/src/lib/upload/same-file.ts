// "Choose the same video" check before resuming (ST-017 U-04; flows D-3). The browser cannot
// reopen a file after the tab closed, so the player picks it again; size, name, date and the
// first MiB must match what the server recorded at creation (api-sprint-01 §5.2).
import { headSha256Hex } from './digest';
import type { UploadState } from '@/lib/api/types';

export type ResumeTarget = Pick<UploadState, 'length' | 'fileName' | 'fileLastModifiedMs' | 'headSha256'>;

export async function checkSameVideo(file: File, upload: ResumeTarget): Promise<boolean> {
  if (file.size !== upload.length) return false;
  if (upload.fileName !== null && file.name !== upload.fileName) return false;
  if (upload.fileLastModifiedMs !== null && file.lastModified !== upload.fileLastModifiedMs) return false;
  if (upload.headSha256 !== null && (await headSha256Hex(file)) !== upload.headSha256) return false;
  return true;
}
