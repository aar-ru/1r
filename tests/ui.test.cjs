const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM,ResourceLoader,VirtualConsole}=require('jsdom');
const {IDBFactory}=require('fake-indexeddb');
const project=path.resolve(__dirname,'..');
const Core=require('../assets/state.js');
const wait=async predicate=>{for(let n=0;n<200;n++){if(await predicate())return;await new Promise(r=>setTimeout(r,10));}throw Error('Condition timed out');};
class Assets extends ResourceLoader {
  fetch(url){const pathname=new URL(url).pathname;return pathname.startsWith('/assets/')?Promise.resolve(fs.readFileSync(path.join(project,pathname))):null;}
}
function setup(page='index.html',{idb=new IDBFactory(),denyStorage=false,channelHub=[]}={}){
  const errors=[];
  const vc=new VirtualConsole();vc.on('jsdomError',error=>errors.push(error));
  const dom=new JSDOM(fs.readFileSync(path.join(project,page),'utf8'),{
    url:`https://affirm.test/${page}`,runScripts:'dangerously',resources:new Assets(),pretendToBeVisual:true,virtualConsole:vc,
    beforeParse(w){
      w.indexedDB=idb;w.structuredClone=structuredClone;w.matchMedia=()=>({matches:false});
      if(idb) {
        const open=idb.open.bind(idb);let latestDatabase;
        idb.open=(...args)=>{
          const request=open(...args);
          request.addEventListener('success',()=>{latestDatabase=request.result;});
          return request;
        };
        w.closeStoreConnection=()=>latestDatabase?.close();
      }
      w.confirm=()=>true;w.document.hasFocus=()=>true;
      if(denyStorage)Object.defineProperty(w,'localStorage',{get(){throw Error('Blocked');}});
      w.BroadcastChannel=class{constructor(){channelHub.push(this);}postMessage(data){for(const ch of channelHub)if(ch!==this)setImmediate(()=>ch.onmessage?.({data}));}close(){}};
      w.IntersectionObserver=class{
        constructor(cb){this.cb=cb;this.elements=new Set();w.testObserver=this;}
        observe(el){this.elements.add(el);}unobserve(el){this.elements.delete(el);}disconnect(){this.elements.clear();}
        show(el){this.cb([...this.elements].map(target=>({target,isIntersecting:target===el,intersectionRatio:target===el?1:0})));}
      };
      w.HTMLElement.prototype.scrollBy=function(options){this.lastScroll=options;};
      w.HTMLElement.prototype.scrollTo=function(options){this.lastScrollTo=options;};
    }
  });
  return {dom,w:dom.window,errors};
}
async function loaded(env,page='index.html'){
  await wait(()=>env.w.AffirmStore && (page==='index.html'?env.w.document.querySelector('.card'):env.w.document.getElementById('activeCount').textContent!=='—'));
  assert.deepEqual(env.errors,[]);
}
test('simultaneous tabs preserve both favorites and serialize duplicate view awards',async t=>{
  const idb=new IDBFactory(),hub=[];
  const a=setup('settings.html',{idb,channelHub:hub}),b=setup('settings.html',{idb,channelHub:hub});
  t.after(()=>{a.w.close();b.w.close();});await Promise.all([loaded(a,'settings.html'),loaded(b,'settings.html')]);
  await Promise.all([
    a.w.AffirmStore.transaction(s=>Core.toggleSaved(s,a.w.AffirmCatalog,'u1')),
    b.w.AffirmStore.transaction(s=>Core.toggleSaved(s,b.w.AffirmCatalog,'u2'))
  ]);
  assert.deepEqual((await a.w.AffirmStore.read()).saved.sort(),['u1','u2']);
  const {state}=await a.w.AffirmStore.transaction(s=>Core.ensureRound(s,a.w.AffirmCatalog));
  const id=state.round.order[0],round=state.round.id;
  await Promise.all([a.w.AffirmStore.transaction(s=>Core.view(s,a.w.AffirmCatalog,id,round,'2026-09-17')),b.w.AffirmStore.transaction(s=>Core.view(s,b.w.AffirmCatalog,id,round,'2026-09-17'))]);
  assert.equal((await a.w.AffirmStore.read()).game.totalCards,1);
  await Promise.all([a.w.AffirmStore.transaction(s=>Core.addTime(s,100,300)),b.w.AffirmStore.transaction(s=>Core.addTime(s,300,500))]);
  const after=await a.w.AffirmStore.read();assert.equal(Object.values(after.days).reduce((n,d)=>n+d.timeMs,0),400);
});
test('rendering 14 cards consumes nothing; reload resumes the viewed card without extra XP',async t=>{
  const idb=new IDBFactory();const a=setup('index.html',{idb});t.after(()=>a.w.close());await loaded(a);
  let state=await a.w.AffirmStore.read();assert.equal(state.round.seen.length,0);assert.equal(a.w.document.querySelectorAll('.card').length,14);
  const first=a.w.document.querySelector('.card');a.w.testObserver.show(first);
  await wait(async()=>(await a.w.AffirmStore.read()).round.seen.length===1);
  const b=setup('index.html',{idb});t.after(()=>b.w.close());await loaded(b);
  const resumed=b.w.document.querySelector('.card');assert.equal(resumed.dataset.id,first.dataset.id);
  b.w.testObserver.show(resumed);await wait(()=>b.w.document.querySelector('.view-count').textContent==='1');
  state=await b.w.AffirmStore.read();assert.equal(state.game.totalXp,1);assert.equal(state.round.seen.length,1);
});
test('untrusted text renders literally in the feed and saved drawer',async t=>{
  const e=setup();t.after(()=>e.w.close());await loaded(e);
  const text='<img src=x onerror="window.injected=true"><b>Affirm</b>';
  await e.w.AffirmStore.transaction(s=>{s.deleted=e.w.AffirmCatalog.items.map(x=>x.id);s.custom=[{id:'c-test',theme:'self',text}];s.saved=['c-test'];Core.ensureRound(s,e.w.AffirmCatalog);});
  await wait(()=>e.w.document.querySelector('.text')?.textContent===text);
  assert.equal(e.w.document.querySelectorAll('#feed img,#feed b').length,0);assert.equal(e.w.injected,undefined);
  e.w.document.querySelector('.open-saved').click();assert.equal(e.w.document.querySelector('.saved-card p').textContent,text);
  assert.equal(e.w.document.querySelectorAll('#savedList img,#savedList b').length,0);
});
test('empty deck offers settings, never resurrecting a deleted affirmation',async t=>{
  const e=setup();t.after(()=>e.w.close());await loaded(e);
  await e.w.AffirmStore.transaction(s=>{s.deleted=e.w.AffirmCatalog.items.map(x=>x.id);Core.ensureRound(s,e.w.AffirmCatalog);});
  assert.equal(e.w.document.querySelectorAll('.card').length,0);assert.match(e.w.document.querySelector('#feed').textContent,/пока нет/);
  assert.equal(e.w.document.querySelector('#feed a').getAttribute('href'),'settings.html');
});
test('space on a button is not hijacked; keyboard paging uses the feed height',async t=>{
  const e=setup();t.after(()=>e.w.close());await loaded(e);
  const feed=e.w.document.getElementById('feed');Object.defineProperty(feed,'clientHeight',{value:800});
  const button=e.w.document.querySelector('.favorite');
  const space=new e.w.KeyboardEvent('keydown',{key:' ',bubbles:true,cancelable:true});button.dispatchEvent(space);
  assert.equal(space.defaultPrevented,false);assert.equal(feed.lastScroll,undefined);
  feed.dispatchEvent(new e.w.KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true}));
  assert.equal(feed.lastScroll.top,800);
});
test('settings reject duplicates, preserve custom deletions for restore and save edits',async t=>{
  const e=setup('settings.html');t.after(()=>e.w.close());await loaded(e,'settings.html');
  const d=e.w.document;
  d.getElementById('newText').value='Я достоин успеха.';d.getElementById('addBtn').click();
  await wait(()=>d.getElementById('notice').textContent.includes('уже есть'));
  assert.equal((await e.w.AffirmStore.read()).custom.length,0);
  d.getElementById('newText').value='Тест сохранения';d.getElementById('addBtn').click();
  await wait(()=>d.getElementById('customCount').textContent==='1');
  d.getElementById('search').value='Тест сохранения';d.getElementById('search').dispatchEvent(new e.w.Event('input'));
  d.querySelector('.edit').click();d.getElementById('editText').value='Тест изменения';d.getElementById('saveEdit').click();
  await wait(()=>!d.getElementById('editBackdrop').classList.contains('open'));
  assert.equal((await e.w.AffirmStore.read()).custom[0].text,'Тест изменения');
  d.getElementById('search').value='Тест изменения';d.getElementById('search').dispatchEvent(new e.w.Event('input'));
  d.querySelector('.delete').click();await wait(()=>d.getElementById('deletedCount').textContent==='1');
  assert.equal((await e.w.AffirmStore.read()).custom.length,1);
  d.getElementById('restoreBtn').click();await wait(()=>d.getElementById('deletedCount').textContent==='0');
  assert.equal(d.querySelector('.item-text').textContent,'Тест изменения');
});
test('back-forward cache return reloads content edited in another page',async t=>{
  const idb=new IDBFactory(),a=setup('index.html',{idb}),b=setup('settings.html',{idb});
  t.after(()=>{a.w.close();b.w.close();});await Promise.all([loaded(a),loaded(b,'settings.html')]);
  const id=a.w.document.querySelector('.card').dataset.id;
  a.w.testObserver.show(a.w.document.querySelector('.card'));
  await wait(async()=>(await a.w.AffirmStore.read()).round.resumeId===id);
  await b.w.AffirmStore.transaction(s=>{s.edits[id]={theme:'self',text:'Изменено на другой странице'};});
  a.w.dispatchEvent(new a.w.PageTransitionEvent('pageshow',{persisted:true}));
  await wait(()=>a.w.document.querySelector('.text')?.textContent==='Изменено на другой странице');
});
test('denied storage never causes a blank settings page',async t=>{
  const e=setup('settings.html',{idb:null,denyStorage:true});
  t.after(()=>e.w.close());await loaded(e,'settings.html');
  assert.equal(e.w.document.getElementById('activeCount').textContent,String(e.w.AffirmState.activeItems(e.w.AffirmState.empty(),e.w.AffirmCatalog).length));
  assert.equal(e.w.document.getElementById('storageWarning').hidden,false);
  e.w.document.getElementById('newText').value='Текст временной сессии';
  e.w.document.getElementById('addBtn').click();
  await wait(()=>e.w.document.getElementById('customCount').textContent==='1');
  assert.deepEqual(e.errors,[]);
});
test('aborted transaction does not report success or overwrite prior data',async t=>{
  const e=setup('settings.html');t.after(()=>e.w.close());await loaded(e,'settings.html');
  await assert.rejects(e.w.AffirmStore.transaction(s=>{s.saved=['u1'];throw Error('Write rejected');}),/Write rejected/);
  assert.deepEqual((await e.w.AffirmStore.read()).saved,[]);
});
test('Safari-style closed IndexedDB connection reconnects for reads and writes',async t=>{
  const e=setup('settings.html');t.after(()=>e.w.close());await loaded(e,'settings.html');
  e.w.closeStoreConnection();
  const written=await e.w.AffirmStore.transaction(s=>{s.saved=['u1'];return 'ok';});
  assert.equal(written.result,'ok');assert.deepEqual(written.state.saved,['u1']);
  e.w.closeStoreConnection();
  assert.deepEqual((await e.w.AffirmStore.read()).saved,['u1']);
  e.w.closeStoreConnection();
  const parallel=await Promise.all([
    e.w.AffirmStore.transaction(s=>{s.saved.push('u2');}),
    e.w.AffirmStore.transaction(s=>{s.saved.push('u3');})
  ]);
  assert.deepEqual(parallel.at(-1).state.saved,['u1','u2','u3']);
  assert.deepEqual(e.errors,[]);
});

test('one persistent header opens progress, traps focus and restores its trigger',async t=>{
  const e=setup();t.after(()=>e.w.close());await loaded(e);
  const d=e.w.document,card=d.querySelector('.card');e.w.testObserver.show(card);
  await wait(()=>d.querySelector('.view-count').textContent==='1');
  assert.equal(d.querySelectorAll('.topbar').length,1);
  assert.equal(d.querySelectorAll('#feed .topbar').length,0);
  assert.equal(d.querySelectorAll('.card:not(.active)').length,13);
  assert.equal(d.querySelector('.card:not(.active)').inert,true);
  const trigger=d.getElementById('openProgress');trigger.focus();trigger.click();
  const modal=d.getElementById('progressDrawer'),close=d.getElementById('closeProgress');
  assert.equal(modal.hidden,false);assert.equal(d.getElementById('feed').inert,true);
  assert.equal(d.getElementById('topbar').inert,true);assert.equal(d.activeElement,close);
  assert.equal(modal.querySelector('.xp-count').textContent,'1');
  assert.equal(modal.querySelectorAll('#achievements li').length,9);
  const tab=new e.w.KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true});close.dispatchEvent(tab);
  assert.equal(tab.defaultPrevented,true);assert.equal(d.activeElement,close);
  close.dispatchEvent(new e.w.KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
  assert.equal(modal.hidden,true);assert.equal(d.activeElement,trigger);
  assert.equal(d.getElementById('feed').inert,false);assert.equal(d.getElementById('topbar').inert,false);
});
test('wheel inertia pages once, while zoom and scrolling long text stay native',async t=>{
  const e=setup();t.after(()=>e.w.close());await loaded(e);
  const feed=e.w.document.getElementById('feed'),text=e.w.document.querySelector('.text');
  Object.defineProperty(feed,'clientHeight',{value:600});
  const movements=[];feed.scrollBy=options=>movements.push(options.top);
  const wheel=(target,options)=>{const event=new e.w.WheelEvent('wheel',{deltaY:180,bubbles:true,cancelable:true,...options});target.dispatchEvent(event);return event;};
  for(let i=0;i<12;i++)assert.equal(wheel(feed).defaultPrevented,true);
  assert.deepEqual(movements,[600]);
  assert.equal(wheel(feed,{ctrlKey:true}).defaultPrevented,false);
  assert.equal(wheel(feed,{deltaX:300}).defaultPrevented,false);
  Object.defineProperty(text,'clientHeight',{value:150});Object.defineProperty(text,'scrollHeight',{value:500});
  assert.equal(wheel(text).defaultPrevented,false);
  const down=new e.w.KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true,cancelable:true});text.dispatchEvent(down);
  assert.equal(down.defaultPrevented,false);
  await new Promise(r=>setTimeout(r,410));
  text.scrollTop=350;assert.equal(wheel(text).defaultPrevented,true);
  assert.deepEqual(movements,[600,600]);
  await new Promise(r=>setTimeout(r,410));
  assert.equal(wheel(feed,{deltaY:-3,deltaMode:1}).defaultPrevented,true);
  assert.deepEqual(movements,[600,600,-600]);
});
test('a short vertical swipe pages instantly once and leaves long text scrolling native',async t=>{
  const e=setup();t.after(()=>e.w.close());await loaded(e);
  const feed=e.w.document.getElementById('feed'),text=e.w.document.querySelector('.text');
  Object.defineProperty(feed,'clientHeight',{value:600});
  const movements=[];feed.scrollTo=options=>movements.push(options);
  const touch=(type,target,x,y)=>{
    const event=new e.w.Event(type,{bubbles:true,cancelable:true});
    Object.defineProperty(event,'touches',{value:type==='touchend'?[]:[{clientX:x,clientY:y}]});
    target.dispatchEvent(event);return event;
  };
  touch('touchstart',feed,100,500);
  const move=touch('touchmove',feed,102,470);
  assert.equal(move.defaultPrevented,true);
  assert.equal(movements.length,1);assert.equal(movements[0].top,600);assert.equal(movements[0].behavior,'auto');
  touch('touchmove',feed,102,380);
  assert.equal(movements.length,1);
  touch('touchend',feed,102,380);
  touch('touchstart',feed,100,500);touch('touchmove',feed,130,485);touch('touchend',feed,130,485);
  assert.equal(movements.length,1);
  Object.defineProperty(text,'clientHeight',{value:150});Object.defineProperty(text,'scrollHeight',{value:500});
  touch('touchstart',text,100,500);
  const textMove=touch('touchmove',text,100,450);
  assert.equal(textMove.defaultPrevented,false);assert.equal(movements.length,1);
  text.scrollTop=350;
  touch('touchstart',text,100,500);
  assert.equal(touch('touchmove',text,100,450).defaultPrevented,true);
  assert.equal(movements.at(-1).top,600);assert.equal(movements.at(-1).behavior,'auto');
});
test('cards skipped by a fast jump return after the last card and complete the round once',async t=>{
  const e=setup();t.after(()=>e.w.close());await loaded(e);
  await e.w.AffirmStore.transaction(s=>{
    s.deleted=e.w.AffirmCatalog.items.filter(x=>!['u1','u2','u3'].includes(x.id)).map(x=>x.id);
    Core.ensureRound(s,e.w.AffirmCatalog);
  });
  const feed=e.w.document.getElementById('feed'),[first,skipped,last]=[...feed.children];
  e.w.testObserver.show(first);await wait(async()=>(await e.w.AffirmStore.read()).round.seen.length===1);
  e.w.testObserver.show(last);
  await wait(()=>feed.children.length===4);
  let state=await e.w.AffirmStore.read();assert.equal(state.round.complete,false);assert.equal(state.game.cycles,0);
  assert.equal(feed.lastElementChild.dataset.id,skipped.dataset.id);
  e.w.testObserver.show(feed.lastElementChild);
  await wait(async()=>(await e.w.AffirmStore.read()).round.complete);
  state=await e.w.AffirmStore.read();assert.equal(state.game.cycles,1);assert.equal(state.game.totalCards,3);
});
test('long sessions keep a bounded DOM while preserving every unread card in the round',async t=>{
  const e=setup();t.after(()=>e.w.close());await loaded(e);
  const feed=e.w.document.getElementById('feed');
  for(let i=0;i<18;i++) {
    e.w.testObserver.show(feed.lastElementChild);
    await wait(async()=>(await e.w.AffirmStore.read()).round.seen.length===i+1);
    assert.ok(feed.children.length<=60);
  }
  const state=await e.w.AffirmStore.read();
  assert.equal(state.round.order.length,e.w.AffirmState.activeItems(e.w.AffirmState.empty(),e.w.AffirmCatalog).length);assert.equal(state.round.seen.length,18);
  assert.equal(state.game.cycles,0);assert.equal(e.w.document.querySelectorAll('.topbar').length,1);
});

test('completion shows saved totals; reload preserves them; next round advances progress after the daily goal',async t=>{
  const idb=new IDBFactory(),a=setup('index.html',{idb});t.after(()=>a.w.close());await loaded(a);
  await a.w.AffirmStore.transaction(s=>{s.deleted=a.w.AffirmCatalog.items.filter(x=>!['u1','u2','u3'].includes(x.id)).map(x=>x.id);Core.ensureRound(s,a.w.AffirmCatalog);});
  const firstRound=(await a.w.AffirmStore.read()).round.id;
  for(const [i,card] of [...a.w.document.querySelectorAll('.card')].entries()) {
    a.w.testObserver.show(card);await wait(async()=>(await a.w.AffirmStore.read()).round.seen.length===i+1);
  }
  const da=a.w.document;
  await wait(()=>!da.getElementById('rewardOverlay').hidden);
  assert.equal(da.getElementById('rewardTitle').textContent,'Круг 1 завершён!');
  assert.equal(da.getElementById('roundCards').textContent,'3');assert.equal(da.getElementById('roundXp').textContent,'+123 XP');
  assert.equal(da.getElementById('rewardClose').textContent,'Следующий круг');
  assert.equal(da.getElementById('summaryLabel').textContent,'Цель дня ✓');
  assert.equal(da.querySelector('.goal-progress').textContent,'Круг 1: 3/3');
  assert.match(da.getElementById('roundRewards').textContent,/Цель дня выполнена/);
  const b=setup('index.html',{idb});t.after(()=>b.w.close());await loaded(b);
  const db=b.w.document;await wait(()=>!db.getElementById('rewardOverlay').hidden);
  assert.equal((await b.w.AffirmStore.read()).round.id,firstRound);
  assert.equal(db.getElementById('roundXp').textContent,'+123 XP');
  b.w.testObserver.show(db.querySelector('.card'));
  assert.equal((await b.w.AffirmStore.read()).game.totalXp,123);
  db.getElementById('rewardClose').click();
  await wait(()=>db.getElementById('rewardOverlay').hidden);
  const secondRound=(await b.w.AffirmStore.read()).round.id;assert.notEqual(secondRound,firstRound);
  assert.equal(db.querySelector('.goal-progress').textContent,'Круг 2: 0/3');
  assert.equal(db.querySelector('.goal-fill').style.width,'0%');
  b.w.testObserver.show(db.querySelector('.card'));
  await wait(()=>db.querySelector('.goal-progress').textContent==='Круг 2: 1/3');
  assert.ok(parseFloat(db.querySelector('.goal-fill').style.width)>33);
  // Continuing the old summary in another tab must not replace the new round.
  da.getElementById('rewardClose').click();await wait(()=>da.getElementById('rewardOverlay').hidden);
  assert.equal((await a.w.AffirmStore.read()).round.id,secondRound);
  assert.equal((await a.w.AffirmStore.read()).game.totalXp,124);
  for(const [i,card] of [...db.querySelectorAll('.card')].slice(1).entries()) {
    b.w.testObserver.show(card);await wait(async()=>(await b.w.AffirmStore.read()).round.seen.length===i+2);
  }
  assert.equal(db.getElementById('rewardTitle').textContent,'Круг 2 завершён!');
  assert.equal(db.getElementById('roundXp').textContent,'+103 XP');
  assert.equal((await b.w.AffirmStore.read()).game.totalXp,226);
  assert.equal((await b.w.AffirmStore.read()).game.streak,1);
  // Midnight removes yesterday's check without discarding the current round.
  await b.w.AffirmStore.transaction(s=>{delete s.days[Core.dateKey()];});
  assert.equal(db.getElementById('summaryLabel').textContent,'Сегодня');
  assert.equal(db.querySelector('.goal-progress').textContent,'Цель: 0/3');
  assert.deepEqual(a.errors,[]);assert.deepEqual(b.errors,[]);
});
