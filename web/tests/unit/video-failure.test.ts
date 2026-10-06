// QA-S2-UI-03 (ST-037 FE): a video the browser cannot decode is not an expired link. Only a link
// that failed to load says "no longer works"; a codec this browser cannot play says so, with no
// "choose again" loop. Chromium reports both as MEDIA_ERR_SRC_NOT_SUPPORTED (code 4); its message
// tells a failed fetch ("Format error") from a stream it cannot decode (scratch probe 2026-10-06:
// 403/404/abort → "MEDIA_ELEMENT_ERROR: Format error"; the H.264 fixture →
// "DEMUXER_ERROR_NO_SUPPORTED_STREAMS: …").
import { describe, expect, it } from 'vitest';
import { classifyVideoFailure, codecType } from '@/lib/media/playback';

const none = () => '' as const;
const yes = () => 'probably' as const;

describe('codecType', () => {
  it('has no type for an unknown or missing codec', () => {
    expect(codecType(undefined)).toBeNull();
    expect(codecType('prores')).toBeNull();
  });
  it('maps the probed codecs to a type the browser can be asked about', () => {
    expect(codecType('h264')).toBe('video/mp4; codecs="avc1.640028"');
    expect(codecType('HEVC')).toBe('video/mp4; codecs="hvc1.1.6.L120.90"');
    expect(codecType('vp9')).toBe('video/webm; codecs="vp9"');
  });
});

describe('classifyVideoFailure', () => {
  it('no error detail, or no codec known: the link', () => {
    expect(classifyVideoFailure(null, 'h264', none)).toBe('link');
    expect(classifyVideoFailure({ code: 4, message: 'DEMUXER_ERROR_NO_SUPPORTED_STREAMS' }, undefined, none)).toBe('link');
  });
  it('a fetch that failed (403, expired signature) is the link, even where the codec is unsupported', () => {
    expect(classifyVideoFailure({ code: 4, message: 'MEDIA_ELEMENT_ERROR: Format error' }, 'h264', none)).toBe('link');
    expect(classifyVideoFailure({ code: 2, message: '' }, 'h264', none)).toBe('link');
  });
  it('a codec this browser can play: a source error is the link', () => {
    expect(classifyVideoFailure({ code: 4, message: '' }, 'h264', yes)).toBe('link');
  });
  it('a decode error is the browser', () => {
    expect(classifyVideoFailure({ code: 3, message: 'PIPELINE_ERROR_DECODE' }, 'h264', yes)).toBe('unplayable');
  });
  it('a source this browser cannot decode is the browser', () => {
    expect(
      classifyVideoFailure({ code: 4, message: 'DEMUXER_ERROR_NO_SUPPORTED_STREAMS: FFmpegDemuxer: no supported streams' }, 'h264', none),
    ).toBe('unplayable');
    expect(classifyVideoFailure({ code: 4, message: '' }, 'hevc', none)).toBe('unplayable');
  });
});
