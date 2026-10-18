// The outbox store in IndexedDB (ST-063c): database `ra-plan-outbox`, object store `done_ops`
// keyed by `session_id`, so one session holds one op. Sign-out deletes every IndexedDB database
// (lib/session/clear.ts), so no op outlives the session on the device.
import type { DoneOp, OutboxStore } from './plan-outbox';

const DB = 'ra-plan-outbox';
const STORE = 'done_ops';

function done<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export function idbOutboxStore(factory: IDBFactory): OutboxStore {
  let db: Promise<IDBDatabase> | null = null;
  const open = () => {
    db ??= new Promise((resolve, reject) => {
      const request = factory.open(DB, 1);
      request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: 'session_id' });
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => {
        db = null;
        reject(request.error);
      };
    });
    return db;
  };
  async function run<T>(mode: IDBTransactionMode, act: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
    const tx = (await open()).transaction(STORE, mode);
    const committed = new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error);
    });
    const [result] = await Promise.all([done(act(tx.objectStore(STORE))), committed]);
    return result;
  }
  return {
    get: (id) => run('readonly', (s) => s.get(id) as IDBRequest<DoneOp | undefined>),
    put: async (op) => void (await run('readwrite', (s) => s.put({ op_id: op.op_id, session_id: op.session_id }))),
    delete: async (id) => void (await run('readwrite', (s) => s.delete(id))),
    all: () => run('readonly', (s) => s.getAll() as IDBRequest<DoneOp[]>),
  };
}
