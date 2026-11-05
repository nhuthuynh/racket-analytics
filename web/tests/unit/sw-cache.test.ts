// @vitest-environment node
// NFR-067.3 (ST-078e; AQS/STACK-04; G05-06 `npm run test -- sw-cache`): the service worker never
// stores a media response. The real public/sw.js runs in node:vm (fixtures/sw.ts) over a fake
// network and Cache Storage; each test reads what ended up in the cache. A plain app file IS
// stored (positive control, testing-strategy rule 8), so an empty cache is a real result.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { ORIGIN, PLAN_CACHE, dispatch, fakeCaches, loadWorker, request } from './fixtures/sw';

const STATIC_CACHE = 'ra-static-v1';

/** A same-origin answer as the browser hands it to the worker (`type` is 'basic' there). */
function answer(body: string, init: { status?: number; type?: string; headers?: Record<string, string> } = {}): Response {
  const response = new Response(body, {
    status: init.status ?? 200,
    headers: { 'content-type': init.type ?? 'application/javascript', ...init.headers },
  });
  Object.defineProperty(response, 'type', { value: 'basic' });
  return response;
}

function device(network: () => Response) {
  const caches = fakeCaches();
  const sw = loadWorker(caches.api, async () => network());
  const stored = () => [...caches.store.values()].flatMap((entries) => [...entries.keys()]);
  return { sw, stored };
}

describe('service worker cache: media is never stored (NFR-067.3)', () => {
  it('positive control: a content-hashed app file is stored', async () => {
    const { sw, stored } = device(() => answer('console.log(1)'));
    const url = `${ORIGIN}/_next/static/chunks/app-3f2a1b.js`;

    const response = await dispatch(sw, request(url));

    expect(response?.status).toBe(200);
    expect(stored()).toEqual([url]);
  });

  it.each(['mp3', 'm4a', 'aac', 'wav', 'ogg', 'oga', 'ogv', 'opus', 'flac', 'mp4', 'webm'])(
    'leaves a .%s file under the app-file path to the network',
    async (ext) => {
      const { sw, stored } = device(() => answer('bytes', { type: 'audio/mpeg' }));

      const response = await dispatch(sw, request(`${ORIGIN}/_next/static/media/clip.0a1b2c.${ext}`));

      expect(response).toBeUndefined();
      expect(stored()).toEqual([]);
    },
  );

  it.each(['video/mp4', 'video/webm', 'audio/mpeg', 'Audio/Ogg; codecs=opus'])(
    'passes on a %s answer under an app-file path without storing it',
    async (type) => {
      const { sw, stored } = device(() => answer('bytes', { type }));

      const response = await dispatch(sw, request(`${ORIGIN}/_next/static/chunks/clip-9f8e7d`));

      expect(response?.status).toBe(200);
      expect(await response?.text()).toBe('bytes');
      expect(stored()).toEqual([]);
    },
  );

  it('passes on a 206 partial answer without storing it', async () => {
    const { sw, stored } = device(() => answer('part', { status: 206, headers: { 'content-range': 'bytes 0-3/100' } }));

    const response = await dispatch(sw, request(`${ORIGIN}/_next/static/chunks/app-3f2a1b.js`));

    expect(response?.status).toBe(206);
    expect(stored()).toEqual([]);
  });

  it('never keeps a media answer in the plan cache either', async () => {
    const { sw, stored } = device(() => answer('bytes', { type: 'video/mp4' }));

    const response = await dispatch(sw, request(`${ORIGIN}/api/me/plan`));

    expect(response?.status).toBe(200);
    expect(stored().filter((url) => url.includes(PLAN_CACHE) || url.endsWith('/api/me/plan'))).toEqual([]);
  });

  it('the static cache name matches the one sign-out clears', async () => {
    const { STATIC_CACHE: cleared } = await import('@/lib/session/clear');
    expect(cleared).toBe(STATIC_CACHE);
  });

  it('sign-out drops the same media files the worker never stores', async () => {
    const { MEDIA_FILE } = await import('@/lib/session/clear');
    const worker = readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), '../../public/sw.js'), 'utf8');
    const extensions = (source: string) => /\(((?:[a-z0-9]+\|)+[a-z0-9]+)\)/.exec(source)![1]!.split('|').sort();
    expect(extensions(MEDIA_FILE.source)).toEqual(extensions(/const MEDIA = (.+);/.exec(worker)![1]!));
  });
});
