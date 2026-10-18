// Runs public/sw.js in a node:vm context with a fake Cache Storage (ST-063c). `fail` makes one
// storage call reject, as a full quota or blocked storage does in a browser (review PE-1).
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const source = readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), '../../../public/sw.js'), 'utf8');
export const ORIGIN = 'https://app.example';
export const PLAN_CACHE = 'ra-plan-v1';
type Listener = (event: unknown) => void;
type StorageCall = 'open' | 'put' | 'delete' | 'match';

/** A Cache Storage with real Responses, keyed by cache name and URL. */
export function fakeCaches(seed: Record<string, Record<string, Response>> = {}, fail: Partial<Record<StorageCall, Error>> = {}) {
  const store = new Map<string, Map<string, Response>>(
    Object.entries(seed).map(([name, entries]) => [name, new Map(Object.entries(entries))]),
  );
  const key = (r: string | { url: string }) => (typeof r === 'string' ? new URL(r, ORIGIN).href : r.url);
  const call = async <T>(name: StorageCall, run: () => T) => {
    if (fail[name]) throw fail[name];
    return run();
  };
  const open = (name: string) =>
    call('open', () => {
      if (!store.has(name)) store.set(name, new Map());
      const c = store.get(name)!;
      return {
        match: (r: string | { url: string }) => call('match', () => c.get(key(r))?.clone()),
        put: (r: string | { url: string }, res: Response) => call('put', () => void c.set(key(r), res)),
        delete: (r: string | { url: string }) => call('delete', () => c.delete(key(r))),
        addAll: async () => undefined,
        keys: async () => [...c.keys()].map((url) => ({ url })),
      };
    });
  return {
    store,
    api: {
      open,
      keys: async () => [...store.keys()],
      delete: async (name: string) => store.delete(name),
      match: (r: string) =>
        call('match', () => [...store.values()].map((c) => c.get(key(r))).find(Boolean)?.clone()),
    },
  };
}

export function loadWorker(caches: unknown, fetch: unknown) {
  const listeners: Record<string, Listener> = {};
  const self = {
    location: { origin: ORIGIN },
    addEventListener: (type: string, fn: Listener) => {
      listeners[type] = fn;
    },
    skipWaiting: () => Promise.resolve(),
    clients: { claim: () => Promise.resolve() },
  };
  // `new Date()` in the worker reads the test's clock at call time, so vi.setSystemTime applies.
  const now = new Proxy(Date, { construct: (_d, args: []) => new globalThis.Date(...args) });
  vm.runInNewContext(source, { self, URL, caches, fetch, Response, Headers, Date: now });
  return listeners;
}

export function request(url: string, mode = 'cors', method = 'GET') {
  return { url, method, mode, headers: { has: () => false } };
}

/** The promise the worker passed to respondWith, or undefined when it left the request alone. */
export async function dispatch(listeners: Record<string, Listener>, req: ReturnType<typeof request>) {
  let response: Promise<Response> | undefined;
  listeners.fetch!({ request: req, respondWith: (r: Promise<Response>) => (response = r) });
  return response;
}
