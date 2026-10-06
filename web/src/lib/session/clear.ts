// Sign-out clears the device (ST-014; FR-011, NFR-067; api-sprint-01 §2.3; ASVS 14.3.1-14.3.3).
// Local and session storage, every IndexedDB database and every Cache Storage entry that is not
// a content-hashed static file or the offline page (they hold no authenticated data; the
// service worker keeps them so the offline A-01 page still works). Each step is independent:
// one blocked store never stops the others.

/** Must match CACHE_NAME in public/sw.js. */
export const STATIC_CACHE = 'ra-static-v1';
const KEEP_IN_STATIC = /^\/(_next\/static\/|offline\.(html|css)$)/;

interface StorageLike {
  clear(): void;
}
interface DeleteRequest {
  onsuccess: unknown;
  onerror: unknown;
  onblocked: unknown;
}
interface IndexedDbLike {
  databases?: () => Promise<{ name?: string }[]>;
  deleteDatabase(name: string): DeleteRequest;
}
interface CacheLike {
  keys(): Promise<readonly { url: string }[]>;
  delete(request: { url: string }): Promise<boolean>;
}
interface CacheStorageLike {
  keys(): Promise<string[]>;
  delete(name: string): Promise<boolean>;
  open(name: string): Promise<CacheLike>;
}

export interface ClientStores {
  localStorage?: StorageLike | null;
  sessionStorage?: StorageLike | null;
  indexedDB?: IndexedDbLike | null;
  caches?: CacheStorageLike | null;
}

function deleteDatabase(idb: IndexedDbLike, name: string): Promise<void> {
  return new Promise((resolve) => {
    const request = idb.deleteDatabase(name);
    const done = () => resolve();
    request.onsuccess = done;
    request.onerror = done;
    request.onblocked = done;
  });
}

async function attempt(step: () => unknown): Promise<void> {
  try {
    await step();
  } catch {
    // Blocked or unavailable store: nothing to clear there.
  }
}

export async function clearClientData(stores: ClientStores): Promise<void> {
  await attempt(() => stores.localStorage?.clear());
  await attempt(() => stores.sessionStorage?.clear());
  await attempt(async () => {
    const idb = stores.indexedDB;
    if (!idb?.databases) return;
    const names = (await idb.databases()).map((d) => d.name).filter((n): n is string => !!n);
    await Promise.all(names.map((name) => deleteDatabase(idb, name)));
  });
  await attempt(async () => {
    const caches = stores.caches;
    if (!caches) return;
    for (const name of await caches.keys()) {
      if (name !== STATIC_CACHE) {
        await caches.delete(name);
        continue;
      }
      const cache = await caches.open(name);
      for (const request of await cache.keys()) {
        if (!KEEP_IN_STATIC.test(new URL(request.url).pathname)) await cache.delete(request);
      }
    }
  });
}

/** The browser's own stores, each looked up defensively (a getter may throw). */
export function browserStores(): ClientStores {
  const get = <T,>(read: () => T): T | null => {
    try {
      return read() ?? null;
    } catch {
      return null;
    }
  };
  return {
    localStorage: get(() => window.localStorage),
    sessionStorage: get(() => window.sessionStorage),
    indexedDB: get(() => window.indexedDB as unknown as IndexedDbLike),
    caches: get(() => (typeof caches === 'undefined' ? null : (caches as unknown as CacheStorageLike))),
  };
}
