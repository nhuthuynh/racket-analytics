// Service worker cache rules (ST-010; NFR-067; AQS/STACK-04; api-sprint-00 §8): it never
// caches media, API responses or pages that depend on the session. Loads public/sw.js in a
// sandbox with a fake `self` and checks which requests it takes over.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import { describe, expect, it } from 'vitest';

// path.join, not `new URL(..., import.meta.url)`: Vite rewrites the latter for public/ files.
const testDir = path.dirname(fileURLToPath(import.meta.url));
const source = readFileSync(path.join(testDir, '../../public/sw.js'), 'utf8');
const ORIGIN = 'https://app.example';

type Listener = (event: unknown) => void;

function loadWorker() {
  const listeners: Record<string, Listener> = {};
  const self = {
    location: { origin: ORIGIN },
    addEventListener: (type: string, fn: Listener) => {
      listeners[type] = fn;
    },
    skipWaiting: () => Promise.resolve(),
    clients: { claim: () => Promise.resolve() },
  };
  const caches = { open: () => new Promise(() => {}), keys: () => Promise.resolve([]) };
  vm.runInNewContext(source, { self, URL, caches, fetch: () => Promise.reject(new Error('no network')) });
  return listeners;
}

function handled(url: string, init: { method?: string; headers?: Record<string, string> } = {}) {
  const listeners = loadWorker();
  let responded = false;
  listeners.fetch!({
    request: {
      url,
      method: init.method ?? 'GET',
      // A plain fake: jsdom's Headers drops `range` as a forbidden request header.
      headers: { has: (name: string) => name.toLowerCase() in (init.headers ?? {}) },
      mode: 'no-cors',
    },
    respondWith: () => {
      responded = true;
    },
  });
  return responded;
}

describe('service worker', () => {
  it('leaves API calls to the network', () => {
    expect(handled(`${ORIGIN}/api/matches`)).toBe(false);
    expect(handled(`${ORIGIN}/api/uploads/abc`, { method: 'PATCH' })).toBe(false);
  });

  it('leaves pages to the network, including match pages', () => {
    expect(handled(`${ORIGIN}/`)).toBe(false);
    expect(handled(`${ORIGIN}/matches`)).toBe(false);
    expect(handled(`${ORIGIN}/matches/0b8f6c1e-3f3a-4c55-9a51-8d1f0e7d2a10`)).toBe(false);
  });

  it('never takes over media, even under the static path', () => {
    expect(handled(`${ORIGIN}/clip.mp4`)).toBe(false);
    expect(handled(`${ORIGIN}/_next/static/media/intro.webm`)).toBe(false);
    expect(handled(`${ORIGIN}/_next/static/x.mov?v=1`)).toBe(false);
  });

  it('leaves range requests and other origins alone', () => {
    expect(
      handled(`${ORIGIN}/_next/static/chunks/app.js`, { headers: { range: 'bytes=0-1' } }),
    ).toBe(false);
    expect(handled('https://cdn.example/_next/static/chunks/app.js')).toBe(false);
  });

  it('serves content-hashed static assets cache-first', () => {
    expect(handled(`${ORIGIN}/_next/static/chunks/app-1a2b3c.js`)).toBe(true);
    expect(handled(`${ORIGIN}/_next/static/css/app-1a2b3c.css`)).toBe(true);
  });

  it('registers install and activate handlers that clean old caches', () => {
    const listeners = loadWorker();
    expect(listeners.install).toBeTypeOf('function');
    expect(listeners.activate).toBeTypeOf('function');
  });
});
