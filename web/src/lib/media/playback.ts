// Why a <video> failed (QA-S2-UI-03; ST-037, FR-027). A link that failed to load (expired or
// changed signature, network) is fixed by a fresh link; a codec this browser cannot decode is
// not, so it must not be reported as an expired link (no "choose again" loop).
//
// Browsers report both as MEDIA_ERR_SRC_NOT_SUPPORTED (code 4). The browser is blamed only when
// it says it cannot play the probed codec AND the error is not a failed fetch: Chromium words a
// failed fetch (403, 404, abort) "MEDIA_ELEMENT_ERROR: Format error" and an undecodable stream
// "DEMUXER_ERROR_NO_SUPPORTED_STREAMS: …" (scratch probe, Playwright Chromium 1194, 2026-10-06).
// The message is non-standard, so any doubt falls back to "the link" (judgment: a fresh link is
// the cheaper wrong guess).

export type VideoFailure = 'link' | 'unplayable';

const MEDIA_ERR_NETWORK = 2;
const MEDIA_ERR_DECODE = 3;
const MEDIA_ERR_SRC_NOT_SUPPORTED = 4;

const TYPES: Record<string, string> = {
  h264: 'video/mp4; codecs="avc1.640028"',
  avc1: 'video/mp4; codecs="avc1.640028"',
  hevc: 'video/mp4; codecs="hvc1.1.6.L120.90"',
  h265: 'video/mp4; codecs="hvc1.1.6.L120.90"',
  vp9: 'video/webm; codecs="vp9"',
  vp8: 'video/webm; codecs="vp8"',
  av1: 'video/mp4; codecs="av01.0.08M.08"',
};

/** The MIME type to ask `canPlayType` about for a probed codec name, or null when unknown. */
export function codecType(codec: string | null | undefined): string | null {
  if (!codec) return null;
  return TYPES[codec.toLowerCase()] ?? null;
}

export function classifyVideoFailure(
  error: { code: number; message?: string } | null | undefined,
  codec: string | null | undefined,
  canPlayType: (type: string) => CanPlayTypeResult,
): VideoFailure {
  if (!error) return 'link';
  if (error.code === MEDIA_ERR_DECODE) return 'unplayable';
  if (error.code === MEDIA_ERR_NETWORK || error.code !== MEDIA_ERR_SRC_NOT_SUPPORTED) return 'link';
  const type = codecType(codec);
  if (!type || canPlayType(type) !== '') return 'link';
  return /format error/i.test(error.message ?? '') ? 'link' : 'unplayable';
}
