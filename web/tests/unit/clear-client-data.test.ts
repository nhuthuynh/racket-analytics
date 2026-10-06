// Sign-out clears the device (ST-014; FR-011, NFR-067; api-sprint-01 §2.3; ASVS 14.3.1-14.3.3).
import { describe, expect, it, vi } from 'vitest';
import { clearClientData, STATIC_CACHE } from '@/lib/session/clear';

function fakeStorage(entries: Record<string, string>) {
  const data = new Map(Object.entries(entries));
  return {
    get length() {
      return data.size;
    },
    clear: vi.fn(() => data.clear()),
    data,
  };
}

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

describe('clearClientData', () => {
  it('empties local and session storage', async () => {
    const local = fakeStorage({ 'tus::x': '{}', other: '1' });
    const session = fakeStorage({ draft: 'Ivy' });
    await clearClientData({ localStorage: local, sessionStorage: session });
    expect(local.data.size + session.data.size).toBe(0);
  });

  it('deletes every IndexedDB database it can list', async () => {
    const deleted: string[] = [];
    const indexedDB = {
      databases: async () => [{ name: 'a' }, { name: 'b' }, {}],
      deleteDatabase: (name: string) => {
        deleted.push(name);
        const request = { onsuccess: null as null | (() => void), onerror: null, onblocked: null };
        queueMicrotask(() => request.onsuccess?.());
        return request;
      },
    };
    await clearClientData({ indexedDB });
    expect(deleted).toEqual(['a', 'b']);
  });

  it('deletes every cache except the static app shell, and anything but static files inside it', async () => {
    const caches = fakeCaches({
      [STATIC_CACHE]: ['https://app.example/_next/static/chunks/a.js', 'https://app.example/offline.html', 'https://app.example/matches'],
      'some-old-cache': ['https://app.example/api/matches'],
    });
    await clearClientData({ caches });
    expect([...caches.stores.keys()]).toEqual([STATIC_CACHE]);
    expect([...caches.stores.get(STATIC_CACHE)!]).toEqual([
      'https://app.example/_next/static/chunks/a.js',
      'https://app.example/offline.html',
    ]);
  });

  it('keeps going when one store throws (private mode, blocked storage)', async () => {
    const local = { get length() { return 0; }, clear: () => { throw new Error('SecurityError'); } };
    const session = fakeStorage({ draft: 'Ivy' });
    await expect(clearClientData({ localStorage: local, sessionStorage: session })).resolves.toBeUndefined();
    expect(session.data.size).toBe(0);
  });
});
