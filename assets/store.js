(function () {
  'use strict';
  const Core = window.AffirmState;
  const listeners = new Set();
  let database, snapshot, temporary = false, writeQueue = Promise.resolve();
  const channel = typeof BroadcastChannel === 'function' ? new BroadcastChannel('affirm-state-v3') : null;
  function legacy() {
    const keys = [];
    try { for (let i=0;i<localStorage.length;i++) keys.push(localStorage.key(i)); } catch {}
    return Core.migrate(key => { try { return localStorage.getItem(key); } catch { return null; } }, keys);
  }
  const ready = new Promise((resolve, reject) => {
    try {
      const request = indexedDB.open('affirm-v3', 1);
      request.onupgradeneeded = () => request.result.createObjectStore('state');
      request.onsuccess = () => { database = request.result; database.onversionchange = () => database.close(); resolve(); };
      request.onerror = () => reject(request.error);
      request.onblocked = () => reject(new Error('Хранилище занято другой версией приложения. Закрой другие вкладки.'));
    } catch (error) { reject(error); }
  }).catch(() => { temporary = true; snapshot = legacy(); });
  function emit() {
    for (const listener of listeners) listener(snapshot);
  }
  async function read() {
    await ready;
    if (temporary) return structuredClone(snapshot);
    return new Promise((resolve, reject) => {
      const tx = database.transaction('state', 'readonly');
      const request = tx.objectStore('state').get('current');
      request.onsuccess = () => { snapshot = request.result || legacy(); };
      tx.oncomplete = () => resolve(structuredClone(snapshot));
      tx.onabort = () => reject(tx.error || new Error('Не удалось прочитать данные.'));
    });
  }
  function transaction(change) {
    // IndexedDB serializes read/write transactions across tabs. Always mutate the latest record.
    const operation = writeQueue.then(async () => {
      await ready;
      if (temporary) {
        const state = structuredClone(snapshot);
        const result = change(state);
        state.revision++; snapshot = state; emit();
        return { state: structuredClone(snapshot), result };
      }
      return new Promise((resolve,reject) => {
        const tx = database.transaction('state','readwrite');
        const store = tx.objectStore('state');
        const request = store.get('current');
        let next, result, failure;
        request.onsuccess = () => {
          try {
            next = request.result || legacy();
            result = change(next);
            next.revision = (next.revision || 0)+1;
            store.put(next,'current');
          } catch (error) { failure=error; tx.abort(); }
        };
        tx.oncomplete = () => {
          snapshot=next; emit();
          channel?.postMessage({revision:next.revision});
          // Storage events cover browsers without BroadcastChannel. This key contains no user data.
          try { localStorage.setItem('affirm_v3_changed', Core.token()); } catch {}
          resolve({state:structuredClone(next),result});
        };
        tx.onabort = () => reject(failure || new Error('Не удалось сохранить изменения. Освободи место и попробуй снова.'));
      });
    });
    writeQueue = operation.catch(()=>{});
    return operation;
  }
  async function refresh() {
    try { await read(); emit(); } catch (error) { window.dispatchEvent(new CustomEvent('affirm-error',{detail:error.message})); }
  }
  if (channel) channel.onmessage = refresh;
  window.addEventListener('storage', event => { if (event.key === 'affirm_v3_changed') refresh(); });
  window.addEventListener('pageshow', refresh);
  window.addEventListener('focus', refresh);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  window.AffirmStore = { read, transaction, subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); }, get temporary() { return temporary; } };
})();
