// SHA-256 helpers for the tus checksum extension and the resume check (ST-017;
// api-sprint-01 §6.3 head_sha256, §6.5 Upload-Checksum). Web Crypto only; nothing is stored.

/** The head range the server compares at offset 0: the first 1 MiB (or the whole file). */
export const HEAD_BYTES = 1024 * 1024;

function readBytes(blob: Blob): Promise<ArrayBuffer> {
  if (typeof blob.arrayBuffer === 'function') return blob.arrayBuffer();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(reader.error);
    reader.readAsArrayBuffer(blob);
  });
}

async function digest(blob: Blob): Promise<Uint8Array> {
  return new Uint8Array(await crypto.subtle.digest('SHA-256', await readBytes(blob)));
}

/** Base64 digest for `Upload-Checksum: sha256 <base64>`. */
export async function sha256Base64(blob: Blob): Promise<string> {
  let binary = '';
  for (const byte of await digest(blob)) binary += String.fromCharCode(byte);
  return btoa(binary);
}

/** Lowercase hex SHA-256 of the first min(1 MiB, size) bytes (`head_sha256` metadata). */
export async function headSha256Hex(file: Blob): Promise<string> {
  const bytes = await digest(file.slice(0, HEAD_BYTES));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}
