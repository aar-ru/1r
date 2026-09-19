(function () {
  'use strict';
  const Core = window.AffirmState;
  const listeners = new Set();
  const pendingTransactions = new Set(), WAIT_MS = 4000;
  let database, opening, snapshot, temporary = false, writeQueue = Promise.resolve();
  let suspended = false;
  const pausedError=()=>Object.assign(new DOMException('Страница приостановлена.','AbortError'),{pageHidden:true});
  const channel = typeof BroadcastChannel === 'function' ? new BroadcastChannel('affirm-state-v3') : null;
  function legacy() {
    const keys = [];
    try { for (let i=0;i<localStorage.length;i++) keys.push(localStorage.key(i)); } catch {}
    return Core.migrate(key => { try { return localStorage.getItem(key); } catch { return null; } }, keys);
  }
  function openDatabase() {
    if(suspended) return Promise.reject(pausedError());
    if (database) return Promise.resolve(database);
    if (opening) return opening;
    opening = new Promise((resolve, reject) => {
      let settled=false;
      const fail=error=>{if(!settled){settled=true;clearTimeout(timer);reject(error);}};
      const timer=setTimeout(()=>fail(new DOMException('Не удалось открыть сохранённые данные. Попробуй ещё раз.','TimeoutError')),WAIT_MS);
      try {
      const request = indexedDB.open('affirm-v3', 1);
      request.onupgradeneeded = () => {
        if(settled || suspended) { request.transaction.abort(); return; }
        request.result.createObjectStore('state');
      };
      request.onsuccess = () => {
        if(settled || suspended) {request.result.close();fail(pausedError());return;}
        settled=true;clearTimeout(timer);
        const opened=request.result; database=opened;
        opened.onversionchange=()=>{ opened.close(); if(database===opened) database=undefined; };
        // Safari may close an IndexedDB connection while a tab is suspended.
        opened.onclose=()=>{ if(database===opened) database=undefined; };
        resolve(opened);
      };
      request.onerror = () => fail(request.error);
      request.onblocked = () => fail(new DOMException('Хранилище занято другой версией приложения. Закрой другие вкладки.','TimeoutError'));
      } catch (error) { fail(error); }
    }).finally(()=>{opening=undefined;});
    return opening;
  }
  const ready = openDatabase().catch(error => {
    // Only an unavailable/denied API uses a temporary session. Transient failures retry the real data.
    if(!['SecurityError','NotSupportedError','ReferenceError','TypeError'].includes(error.name)) return;
    temporary = true; snapshot = legacy();
  });
  function disconnect(opened) {
    try { opened?.close(); } catch {}
    if(database===opened) database=undefined;
  }
  function reconnect(error, opened) {
    if(suspended || !error || !['InvalidStateError','TransactionInactiveError','AbortError','TimeoutError'].includes(error.name)) return false;
    disconnect(opened);
    return true;
  }
  function watchTransaction(tx, opened, reject) {
    let settled=false;
    const finish=()=>{
      if(settled) return false;
      settled=true;clearTimeout(timer);pendingTransactions.delete(cancel);return true;
    };
    const cancel=(timedOut=false)=>{
      if(settled) return;
      let error=timedOut ? new DOMException('Сохранённые данные не ответили. Попробуй ещё раз.','TimeoutError') : pausedError();
      try { tx.abort(); }
      catch {
        // A commit may already be in progress. Never replay a possibly committed write.
        if(!timedOut) return;
        error=new Error('Браузер не подтвердил сохранение. Обнови страницу, чтобы проверить данные.');
      }
      disconnect(opened);
      if(finish()) reject(error);
    };
    const timer=setTimeout(()=>cancel(true),WAIT_MS);
    pendingTransactions.add(cancel);
    return {finish,get settled(){return settled;}};
  }
  function emit() {
    for (const listener of listeners) listener(snapshot);
  }
  async function read() {
    await ready;
    if(suspended) throw pausedError();
    if (temporary) return structuredClone(snapshot);
    for(let attempt=0;attempt<2;attempt++) {
      let opened;
      try {
        opened=await openDatabase();
        return await new Promise((resolve, reject) => {
          let tx;
          try { tx=opened.transaction('state','readonly'); }
          catch(error) { reject(error); return; }
          const watch=watchTransaction(tx,opened,reject);
          const request=tx.objectStore('state').get('current');
          let next;
          request.onsuccess=()=>{if(!watch.settled) next=request.result || legacy();};
          tx.oncomplete=()=>{if(watch.finish()){snapshot=next;resolve(structuredClone(next));}};
          tx.onabort=()=>{if(watch.finish()) reject(tx.error || new DOMException('Чтение прервано.','AbortError'));};
          tx.onerror=()=>{};
        });
      } catch(error) {
        if(attempt || !reconnect(error,opened)) throw error;
      }
    }
  }
  function transaction(change) {
    // IndexedDB serializes read/write transactions across tabs. Always mutate the latest record.
    const operation = writeQueue.then(async () => {
      await ready;
      if(suspended) throw pausedError();
      if (temporary) {
        const state = structuredClone(snapshot);
        const result = change(state);
        state.revision++; snapshot = state; emit();
        return { state: structuredClone(snapshot), result };
      }
      for(let attempt=0;attempt<2;attempt++) {
        let opened;
        let changeFailed=false;
        try {
        opened=await openDatabase();
        return await new Promise((resolve,reject) => {
        let tx;
        try { tx=opened.transaction('state','readwrite'); }
        catch(error) { reject(error); return; }
        const watch=watchTransaction(tx,opened,reject);
        const store = tx.objectStore('state');
        const request = store.get('current');
        let next, result, failure;
        request.onsuccess = () => {
          if(watch.settled) return;
          try {
            next = request.result || legacy();
            result = change(next);
            next.revision = (next.revision || 0)+1;
            store.put(next,'current');
          } catch (error) { failure=error; changeFailed=true; tx.abort(); }
        };
        tx.oncomplete = () => {
          if(!watch.finish()) return;
          snapshot=next;
          resolve({state:structuredClone(next),result});
          emit();
          channel?.postMessage({revision:next.revision});
          // Storage events cover browsers without BroadcastChannel. This key contains no user data.
          try { localStorage.setItem('affirm_v3_changed', Core.token()); } catch {}
        };
        tx.onabort = () => {if(watch.finish()) reject(failure || tx.error || new DOMException('Запись прервана.','AbortError'));};
        tx.onerror = () => {};
      }); } catch(error) {
          if(attempt || changeFailed || !reconnect(error,opened)) throw error;
        }
      }
    });
    writeQueue = operation.catch(()=>{});
    return operation;
  }
  async function refresh() {
    try { await read(); emit(); } catch (error) { if(!error.pageHidden) window.dispatchEvent(new CustomEvent('affirm-error',{detail:error.message})); }
  }
  if (channel) channel.onmessage = refresh;
  window.addEventListener('storage', event => { if (event.key === 'affirm_v3_changed') refresh(); });
  window.addEventListener('pagehide',()=>{
    suspended=true;
    // Release unfinished transactions before this document is frozen in the back/forward cache.
    for(const cancel of [...pendingTransactions]) cancel();
    disconnect(database);
  });
  window.addEventListener('pageshow',()=>{suspended=false;refresh();});
  window.addEventListener('focus', refresh);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  window.AffirmStore = { read, transaction, subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); }, get temporary() { return temporary; } };
})();
