(async function () {
  'use strict';
  const Core = window.AffirmState, Store = window.AffirmStore, Catalog = window.AffirmCatalog;
  const feed = document.getElementById('feed');
  const drawer = document.getElementById('drawer');
  const progressDrawer = document.getElementById('progressDrawer');
  const topbar = document.getElementById('topbar');
  const backdrop = document.getElementById('backdrop');
  const savedList = document.getElementById('savedList');
  const rewardOverlay = document.getElementById('rewardOverlay');
  const rewardClose = document.getElementById('rewardClose');
  const toast = document.getElementById('toast');
  let state, fingerprint = '', plan = [], planned = 0, activeCard, building = false, advancing = false;
  let viewPending = false, previousFocus, sessionMs = 0, lastTick = Date.now(), lastActivity = Date.now();
  let focused = document.hasFocus() && !document.hidden;
  let intervals = [], lastFlush = Date.now(), timerBusy = false;
  const counted = new WeakMap(), rewards = [];
  let rewardShowing = false, summaryRoundId = null;
  let wheelTotal=0, wheelLatched=false, wheelTimer, touchStart=null, touchPaged=false;
  const MAX_CARDS = 60;
  drawer.hidden = progressDrawer.hidden = backdrop.hidden = rewardOverlay.hidden = true;
  drawer.setAttribute('role','dialog'); drawer.setAttribute('aria-modal','true');

  function message(text) {
    toast.textContent = text; toast.classList.add('show');
    clearTimeout(message.timer); message.timer=setTimeout(()=>toast.classList.remove('show'),3500);
  }
  window.addEventListener('affirm-error', e=>message(e.detail));
  function imageFor(item) {
    const images=Catalog.themes[item.theme].images;
    const number=Number(item.id.replace(/\D/g,'')) || 0;
    return images[number % images.length];
  }
  function time(ms) {
    const seconds=Math.floor(Math.max(0,ms)/1000);
    return (seconds>=3600 ? `${String(Math.floor(seconds/3600)).padStart(2,'0')}:` : '') +
      `${String(Math.floor(seconds/60)%60).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`;
  }
  function today() { return state?.days[Core.dateKey()] || {cards:0,timeMs:0,seen:[],completed:false}; }
  function updateHud() {
    if (!state) return;
    const day=today(), game=state.game, items=Core.activeItems(state,Catalog);
    const seen=items.filter(x=>day.seen.includes(x.id)).length;
    const round=state.round;
    const roundNumber=game.cycles+(round?.complete?0:1);
    const roundText=round ? `Круг ${roundNumber}: ${round.seen.length}/${round.order.length}` : 'Нет карточек';
    const recent=game.lastGoalDate===Core.dateKey() || game.lastGoalDate===Core.previousDay(Core.dateKey());
    const values={'.session-timer':time(sessionMs),'.day-timer':time(day.timeMs),'.view-count':day.cards,
      '.cycle-remaining':state.round ? state.round.order.length-state.round.seen.length : 0,
      '.streak-count':recent ? game.streak : 0,'.xp-count':game.totalXp,'.level-count':Math.floor(game.totalXp/250)+1,
      '.total-cards':game.totalCards,'.cycle-count':game.cycles,
      '.round-progress':roundText,
      '.goal-progress':day.completed ? roundText : `Цель: ${seen}/${items.length}`};
    for (const [selector,value] of Object.entries(values)) {
      for (const element of document.querySelectorAll(selector)) element.textContent=value;
    }
    document.getElementById('summaryLabel').textContent=day.completed?'Цель дня ✓':'Сегодня';
    const fraction=day.completed ? (round ? round.seen.length/round.order.length : 0) : (items.length ? seen/items.length : 0);
    document.querySelector('.goal-fill').style.width=`${fraction*100}%`;
    const list=document.getElementById('achievements');
    const earned=game.achievements.join(',');
    if(list.dataset.earned!==earned) {
      list.dataset.earned=earned; list.replaceChildren();
      for(const [key,,emoji,title] of Core.milestones(game)) {
        const item=document.createElement('li'), label=document.createElement('span'), status=document.createElement('span');
        const unlocked=game.achievements.includes(key);
        item.className=unlocked?'earned':''; label.textContent=`${emoji} ${title}`;
        status.textContent=unlocked?'Получено':'Впереди'; item.append(label,status); list.appendChild(item);
      }
    }
  }
  function syncFavorites() {
    if (!state) return;
    for (const button of feed.querySelectorAll('.favorite')) {
      const saved=state.saved.includes(button.closest('.card').dataset.id);
      button.classList.toggle('saved',saved); button.textContent=saved?'♥':'♡';
      button.setAttribute('aria-pressed',String(saved));
    }
    const count=Core.allItems(state,Catalog).filter(x=>state.saved.includes(x.id)).length;
    for (const badge of topbar.querySelectorAll('.count-badge')) { badge.textContent=count; badge.hidden=!count; }
    if (!drawer.hidden) renderSaved();
  }
  function applyState(next) {
    if (state && next.revision < state.revision) return;
    const key=JSON.stringify(Core.activeItems(next,Catalog));
    const changed=key!==fingerprint || state?.round?.id!==next.round?.id;
    state=next;
    fingerprint=key;
    if (changed && !building) buildFeed();
    syncFavorites(); updateHud(); presentReward();
  }
  async function prepare() {
    if (advancing) return;
    advancing=true;
    try {
      const update=await Store.transaction(s=>Core.ensureRound(s,Catalog,Math.random,false));
      applyState(update.state);
    } catch(error) { message(error.message); }
    finally { advancing=false; }
  }
  function makeCard(item) {
    const card=document.createElement('section');
    card.className='card'; card.dataset.id=item.id; card.dataset.roundId=state.round.id; card.inert=true;
    // Only fixed application markup goes through innerHTML. All user strings use textContent.
    card.innerHTML=`<div class="bg"></div><div class="overlay"></div>
      <div class="content"><div class="topic"></div><p class="text" tabindex="0"></p></div>
      <button class="icon-btn favorite" aria-label="Сохранить" aria-pressed="false">♡</button>`;
    card.querySelector('.bg').style.backgroundImage=`url('${imageFor(item)}')`;
    card.querySelector('.topic').textContent=Catalog.themes[item.theme].label;
    const text=card.querySelector('.text'); text.textContent=item.text;
    if(item.text.length>160) card.classList.add('long-text');
    card.querySelector('.favorite').addEventListener('click',async e=>{
      e.stopPropagation(); const button=e.currentTarget; button.disabled=true;
      try {
        const {state:next}=await Store.transaction(s=>Core.toggleSaved(s,Catalog,item.id));
        applyState(next); message(next.saved.includes(item.id)?'Сохранено':'Удалено из сохранённых');
      } catch(error) { message(error.message); }
      finally { button.disabled=false; }
    });
    return card;
  }
  function recoverSkipped() {
    // Fast touch/scrollbar jumps can miss the view threshold. Offer every unseen card again.
    if(!activeCard || viewPending || activeCard!==feed.lastElementChild || planned<plan.length ||
      !state.round || state.round.complete || !state.round.seen.includes(activeCard.dataset.id)) return;
    const pending=Core.preview(state,Catalog).filter(item=>!state.round.seen.includes(item.id));
    if(pending.length) { plan=pending; planned=0; appendCards(); }
  }
  function appendCards(n=10) {
    if (!state?.round) return;
    const fragment=document.createDocumentFragment();
    for(let i=0;i<n && planned<plan.length;i++) {
      const card=makeCard(plan[planned++]); fragment.appendChild(card); observer.observe(card);
    }
    feed.appendChild(fragment); syncFavorites();
    // Keep a bounded recent history; the durable deck lives independently of these DOM nodes.
    if(feed.children.length>MAX_CARDS) {
      const excess=feed.children.length-MAX_CARDS;
      let removed=0;
      for(let i=0;i<excess;i++) {
        const first=feed.firstElementChild;
        if(first===activeCard || first.getBoundingClientRect().bottom>feed.getBoundingClientRect().top) break;
        removed+=first.getBoundingClientRect().height; observer.unobserve(first); first.remove();
      }
      if(removed) { feed.style.scrollBehavior='auto'; feed.scrollTop-=removed; feed.style.scrollBehavior=''; }
    }
  }
  function buildFeed() {
    building=true; observer.disconnect(); activeCard=null; feed.replaceChildren(); feed.scrollTop=0;
    plan=Core.preview(state,Catalog); planned=0;
    if(!Core.activeItems(state,Catalog).length) {
      const empty=document.createElement('div'); empty.className='empty feed-empty';
      const label=document.createElement('p'); label.textContent='В ленте пока нет аффирмаций.';
      const link=document.createElement('a'); link.href='settings.html'; link.textContent='Добавить или восстановить в настройках';
      empty.append(label,link); feed.appendChild(empty);
    } else if(plan.length) appendCards(14);
    else { building=false; prepare(); return; }
    building=false;
  }
  async function recordActive() {
    const card=activeCard, key=Core.dateKey();
    if(!card || viewPending || document.hidden || !document.hasFocus() || !drawer.hidden || !progressDrawer.hidden || !rewardOverlay.hidden || counted.get(card)===key) return;
    viewPending=true;
    tick();
    const pending=intervals; intervals=[];
    try {
      const {state:next,result}=await Store.transaction(s=>{
        for(const [start,end] of pending) Core.addTime(s,start,end);
        return Core.view(s,Catalog,card.dataset.id,card.dataset.roundId,key);
      });
      counted.set(card,key); applyState(next);
      if(next.round?.complete) rewards.length=0;
      else rewards.push(...result);
      presentReward();
    } catch(error) { intervals.unshift(...pending); message(error.message); }
    finally { viewPending=false; recoverSkipped(); if(activeCard!==card) recordActive(); }
  }
  const observer=new IntersectionObserver(entries=>{
    for(const entry of entries) {
      if(!feed.contains(entry.target)) continue;
      const visible=entry.isIntersecting && entry.intersectionRatio>=.65;
      entry.target.classList.toggle('active',visible);
      entry.target.inert=!visible;
      if(visible) {
        activeCard=entry.target; updateHud(); recordActive();
        const index=[...feed.children].indexOf(activeCard);
        if(feed.children.length-index<5) appendCards();
        recoverSkipped();
      }
    }
  },{root:feed,threshold:[.65]});
  function renderSaved() {
    savedList.replaceChildren();
    const items=new Map(Core.allItems(state,Catalog).map(x=>[x.id,x]));
    for(const id of [...state.saved].reverse()) {
      const item=items.get(id); if(!item) continue;
      const card=document.createElement('div'); card.className='saved-card'; card.style.backgroundImage=`url('${imageFor(item)}')`;
      const topic=document.createElement('div'); topic.className='mini-topic'; topic.textContent=Catalog.themes[item.theme].label;
      const text=document.createElement('p'); text.textContent=item.text; card.append(topic,text); savedList.appendChild(card);
    }
    if(!savedList.children.length) {
      const empty=document.createElement('div'); empty.className='empty'; empty.textContent='Здесь появятся аффирмации, которые ты сохранишь сердцем.'; savedList.appendChild(empty);
    }
  }
  function openModal(modal) {
    previousFocus=document.activeElement;
    if(modal===drawer) renderSaved();
    if(modal!==rewardOverlay) { backdrop.hidden=false; backdrop.classList.add('open'); }
    modal.hidden=false; modal.classList.add('open'); feed.inert=topbar.inert=true; feed.style.overflowY='hidden';
    modal.querySelector('button')?.focus();
  }
  function closeModal(modal) {
    modal.hidden=true; modal.classList.remove('open');
    if(modal!==rewardOverlay) { backdrop.hidden=true; backdrop.classList.remove('open'); }
    feed.inert=topbar.inert=false; feed.style.overflowY='auto';
    if(previousFocus?.isConnected) previousFocus.focus({preventScroll:true});
  }
  function presentReward() {
    if(rewardShowing || !state || !drawer.hidden || !progressDrawer.hidden || document.hidden || !document.hasFocus()) return;
    const summary=state.round?.complete ? state.round.summary : null;
    const reward=summary ? {emoji:'🎉',title:`Круг ${summary.number} завершён!`,text:'Все карточки этого круга просмотрены. Можно продолжить в своём темпе.'} : rewards.shift();
    if(!reward) return;
    rewardShowing=true; summaryRoundId=summary?state.round.id:null;
    if(summary) rewards.length=0;
    document.getElementById('rewardEmoji').textContent=reward.emoji;
    document.getElementById('rewardTitle').textContent=reward.title;
    document.getElementById('rewardText').textContent=reward.text;
    const details=document.getElementById('roundSummary');
    details.hidden=!summary;
    rewardOverlay.classList.toggle('round-result',!!summary);
    rewardClose.textContent=summary?'Следующий круг':'Продолжить';
    if(summary) {
      document.getElementById('roundCards').textContent=summary.cards;
      document.getElementById('roundTimeLabel').textContent=summary.fullStats?'Время круга':'Время сегодня';
      document.getElementById('roundTime').textContent=time(summary.timeMs);
      document.getElementById('roundXpLabel').textContent=summary.fullStats?'Заработано за круг':'Бонус за круг';
      document.getElementById('roundXp').textContent=`+${summary.xp} XP`;
      const list=document.getElementById('roundRewards'); list.replaceChildren();
      for(const earned of summary.rewards) {
        const item=document.createElement('li'); item.textContent=`${earned.emoji} ${earned.title}`; list.appendChild(item);
      }
    }
    openModal(rewardOverlay);
    if(state.haptics) { try { navigator.vibrate?.([60,40,60]); } catch {} }
  }
  async function closeReward() {
    if(rewardClose.disabled) return;
    if(summaryRoundId) {
      const completedId=summaryRoundId;
      rewardClose.disabled=true; tick();
      const pending=intervals; intervals=[];
      try {
        const update=await Store.transaction(s=>{
          for(const [start,end] of pending) Core.addTime(s,start,end);
          // Another tab may already have continued. Never replace its new round.
          if(s.round?.id===completedId && s.round.complete) Core.ensureRound(s,Catalog);
        });
        applyState(update.state);
      } catch(error) { intervals.unshift(...pending); message(error.message); return; }
      finally { rewardClose.disabled=false; }
    }
    closeModal(rewardOverlay); rewardShowing=false; summaryRoundId=null;
    presentReward(); recordActive();
  }
  function closeDrawer(modal) { closeModal(modal); presentReward(); recordActive(); }
  document.querySelector('.open-saved').addEventListener('click',()=>openModal(drawer));
  document.getElementById('openProgress').addEventListener('click',()=>openModal(progressDrawer));
  document.getElementById('closeDrawer').addEventListener('click',()=>closeDrawer(drawer));
  document.getElementById('closeProgress').addEventListener('click',()=>closeDrawer(progressDrawer));
  backdrop.addEventListener('click',()=>closeDrawer(drawer.hidden?progressDrawer:drawer));
  rewardClose.addEventListener('click',closeReward);
  rewardOverlay.addEventListener('click',e=>{if(e.target===rewardOverlay) closeReward();});
  document.addEventListener('keydown',e=>{
    const modal=!rewardOverlay.hidden?rewardOverlay:!drawer.hidden?drawer:!progressDrawer.hidden?progressDrawer:null;
    if(modal) {
      if(e.key==='Escape') { e.preventDefault(); modal===rewardOverlay?closeReward():closeDrawer(modal); }
      if(e.key==='Tab') {
        const controls=[...modal.querySelectorAll('button,a[href],input,textarea,select')];
        if(e.shiftKey && document.activeElement===controls[0]) {e.preventDefault();controls.at(-1)?.focus();}
        else if(!e.shiftKey && document.activeElement===controls.at(-1)) {e.preventDefault();controls[0]?.focus();}
      }
      return;
    }
    if(e.target.closest('button,a,input,textarea,select,[contenteditable="true"]') || e.altKey || e.ctrlKey || e.metaKey) return;
    if(['ArrowDown','PageDown',' ','ArrowUp','PageUp'].includes(e.key)) {
      const direction=['ArrowUp','PageUp'].includes(e.key) || (e.key===' ' && e.shiftKey)?-1:1;
      if(canScrollText(e.target,direction)) return;
      e.preventDefault();
      navigate(direction);
    }
  });
  function canScrollText(target,direction) {
    const text=target.closest('.text');
    return text && text.scrollHeight>text.clientHeight+1 &&
      (direction<0 ? text.scrollTop>0 : text.scrollTop+text.clientHeight<text.scrollHeight-1);
  }
  function navigate(direction, align=false) {
    if(state.round?.complete && direction>0) {presentReward();return;}
    if(align) {
      const page=Math.round(feed.scrollTop/feed.clientHeight);
      feed.scrollTo({top:Math.max(0,(page+direction)*feed.clientHeight),behavior:'auto'});
    } else feed.scrollBy({top:feed.clientHeight*direction,behavior:'auto'});
  }
  feed.addEventListener('touchstart',e=>{
    if(e.touches.length!==1 || e.target.closest('button,a,input,textarea,select,[contenteditable="true"]')) {
      touchStart=null; return;
    }
    const touch=e.touches[0];
    touchStart={x:touch.clientX,y:touch.clientY,target:e.target}; touchPaged=false;
  },{passive:true});
  feed.addEventListener('touchmove',e=>{
    if(!touchStart || touchPaged || e.touches.length!==1) return;
    const touch=e.touches[0], dx=touch.clientX-touchStart.x, dy=touchStart.y-touch.clientY;
    if(Math.abs(dy)<24 || Math.abs(dy)<=Math.abs(dx)) return;
    const direction=Math.sign(dy);
    if(canScrollText(touchStart.target,direction)) { touchStart=null; return; }
    e.preventDefault(); touchPaged=true; activity(); navigate(direction,true);
  },{passive:false});
  for(const event of ['touchend','touchcancel']) feed.addEventListener(event,()=>{touchStart=null;touchPaged=false;},{passive:true});
  feed.addEventListener('wheel',e=>{
    if(e.ctrlKey || e.metaKey || !e.deltaY || Math.abs(e.deltaX)>Math.abs(e.deltaY)) return;
    const direction=Math.sign(e.deltaY);
    if(canScrollText(e.target,direction)) return;
    e.preventDefault(); activity();
    clearTimeout(wheelTimer);
    wheelTimer=setTimeout(()=>{wheelTotal=0;wheelLatched=false;},180);
    if(wheelLatched) return;
    const delta=e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?feed.clientHeight:1);
    wheelTotal=Math.sign(wheelTotal)===direction?wheelTotal+delta:delta;
    if(Math.abs(wheelTotal)>=30) {wheelLatched=true;navigate(direction);}
  },{passive:false});
  async function flushTime() {
    if(timerBusy || !intervals.length) return;
    const pending=intervals; intervals=[]; timerBusy=true;
    try { await Store.transaction(s=>{for(const [start,end] of pending) Core.addTime(s,start,end);}); }
    catch(error) { intervals.unshift(...pending); message(error.message); }
    finally { timerBusy=false; }
  }
  function tick() {
    const now=Date.now();
    const end=Math.min(now,lastActivity+30000);
    if(focused && end>lastTick) { intervals.push([lastTick,end]); sessionMs+=end-lastTick; }
    lastTick=now;
    if(now-lastFlush>=2000) { lastFlush=now; flushTime(); }
    updateHud();
  }
  function activity() {
    const now=Date.now(); tick();
    if(now-lastActivity>=30000) sessionMs=0;
    lastActivity=now;
    if(state?.round?.complete) presentReward();
  }
  for(const event of ['pointerdown','touchstart','keydown']) document.addEventListener(event,activity,{passive:true});
  feed.addEventListener('scroll',activity,{passive:true});
  function pause() { tick(); focused=false; flushTime(); }
  async function resume() {
    focused=!document.hidden && document.hasFocus(); lastTick=lastActivity=Date.now(); sessionMs=0;
    try { applyState(await Store.read()); await prepare(); recordActive(); } catch(error) {message(error.message);}
  }
  window.addEventListener('blur',pause); window.addEventListener('pagehide',pause);
  window.addEventListener('focus',resume);
  window.addEventListener('pageshow',e=>{if(e.persisted) resume();});
  document.addEventListener('visibilitychange',()=>document.hidden?pause():resume());
  setInterval(()=>{tick();if(focused) recordActive();},1000);
  Store.subscribe(applyState);
  try {
    await prepare();
    if(Store.temporary) document.getElementById('storageWarning').hidden=false;
    else if(state.migrationNotice) {
      message('Данные перенесены. Текущий круг начат заново для точного учёта.');
      await Store.transaction(s=>{s.migrationNotice=false;});
    }
  } catch(error) { message(error.message); }
})();
