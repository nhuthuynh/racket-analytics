// NFR-067.2-.3 at sign-out (ST-078e; AQS/SEC-05 14.3.1-14.3.3): clearClientData leaves no media
// in any cache, not even in the app-file cache an older worker may have filled, and deletes the
// app's own IndexedDB databases on a browser that cannot list them (indexedDB.databases() is
// missing in some engines). The ST-014 rules stay in clear-client-data.test.ts.
import { describe, expect, it } from 'vitest';
import { KNOWN_DATABASES, STATIC_CACHE, clearClientData } from '@/lib/session/clear';

function fakeCaches(content: Record<string, string[]>) {
  const stores = new Map(Object.entries(content).map(([k, urls]) => [k, new Set(urls)]));
  return {
    stores,
    keys: async () => [...stores.keys()],
    delete: async (name: string) => stores.delete(name),
    open: async (name: string) => ({
      keys: async () => [...(stores.get(name) ?? [])].map((url) => ({ url })),
      delete: async (req: { url: string }) => stores.get(name)?.delete(req.url) ?? false,
    }),
  };
}

function fakeIndexedDb(withList: boolean) {
  const deleted: string[] = [];
  const deleteDatabase = (name: string) => {
    deleted.push(name);
    const request = { onsuccess: null as null | (() => void), onerror: null, onblocked: null };
    queueMicrotask(() => request.onsuccess?.());
    return request;
  };
  return { deleted, idb: withList ? { databases: async () => [{ name: 'other' }], deleteDatabase } : { deleteDatabase } };
}

describe('sign-out hygiene (NFR-067.2-.3)', () => {
  it('removes media files from the app-file cache and keeps the hashed app files', async () => {
    const caches = fakeCaches({
      [STATIC_CACHE]: [
        'https://app.example/_next/static/chunks/a.js',
        'https://app.example/_next/static/media/clip.0a1b2c.mp4',
        'https://app.example/_next/static/media/serve.9f8e.mp3',
        'https://app.example/offline.html',
      ],
    });

    await clearClientData({ caches });

    expect([...caches.stores.get(STATIC_CACHE)!]).toEqual([
      'https://app.example/_next/static/chunks/a.js',
      'https://app.example/offline.html',
    ]);
  });

  it('deletes the app databases by name when the browser cannot list them', async () => {
    const { deleted, idb } = fakeIndexedDb(false);

    await clearClientData({ indexedDB: idb });

    expect(KNOWN_DATABASES).toContain('ra-plan-outbox');
    expect(deleted).toEqual([...KNOWN_DATABASES]);
  });

  it('deletes listed and known databases once each when the browser can list them', async () => {
    const { deleted, idb } = fakeIndexedDb(true);

    await clearClientData({ indexedDB: idb });

    expect([...deleted].sort()).toEqual([...new Set(['other', ...KNOWN_DATABASES])].sort());
  });
});
