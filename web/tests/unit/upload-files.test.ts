// Same-file check for resuming (ST-017 U-04; flows D-3) and the checksums sent with tus
// (api-sprint-01 §6.3 head_sha256, §6.5 Upload-Checksum).
import { describe, expect, it } from 'vitest';
import { checkSameVideo } from '@/lib/upload/same-file';
import { headSha256Hex, HEAD_BYTES, sha256Base64 } from '@/lib/upload/digest';

const bytes = (n: number, fill = 7) => new Uint8Array(n).fill(fill);

describe('digests', () => {
  it('sha256 base64 of a chunk (tus checksum extension)', async () => {
    // sha256("abc") = ungWv48Bz+pBQUDeXa4iI7ADYaOWF3qctBD/YfIAFa0=
    expect(await sha256Base64(new Blob(['abc']))).toBe('ungWv48Bz+pBQUDeXa4iI7ADYaOWF3qctBD/YfIAFa0=');
  });

  it('head hash covers only the first MiB, lowercase hex', async () => {
    const small = new File([bytes(10)], 'a.mp4');
    const big = new File([bytes(HEAD_BYTES), bytes(5, 9)], 'b.mp4');
    const sameHead = new File([bytes(HEAD_BYTES), bytes(50, 1)], 'c.mp4');
    expect(await headSha256Hex(small)).toMatch(/^[0-9a-f]{64}$/);
    expect(await headSha256Hex(big)).toBe(await headSha256Hex(sameHead));
  });
});

describe('checkSameVideo', () => {
  const file = new File([bytes(100)], 'Sat doubles.mp4', { lastModified: 1759480000000 });
  const upload = async (over: Record<string, unknown> = {}) => ({
    length: 100,
    fileName: 'Sat doubles.mp4',
    fileLastModifiedMs: 1759480000000,
    headSha256: await headSha256Hex(file),
    ...over,
  });

  it('accepts the same name, size, date and first bytes', async () => {
    expect(await checkSameVideo(file, await upload())).toBe(true);
  });

  it('refuses another size, name, date or content', async () => {
    expect(await checkSameVideo(file, await upload({ length: 101 }))).toBe(false);
    expect(await checkSameVideo(file, await upload({ fileName: 'clip.mp4' }))).toBe(false);
    expect(await checkSameVideo(file, await upload({ fileLastModifiedMs: 1 }))).toBe(false);
    expect(await checkSameVideo(file, await upload({ headSha256: 'a'.repeat(64) }))).toBe(false);
  });

  it('relies on size and content when the server kept no name or date', async () => {
    expect(await checkSameVideo(file, await upload({ fileName: null, fileLastModifiedMs: null }))).toBe(true);
  });
});
