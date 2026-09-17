(function (root) {
  'use strict';
  const numeric = x => Number.isFinite(Number(x)) ? Math.max(0, Math.floor(Number(x))) : 0;
  const unique = xs => [...new Set(Array.isArray(xs) ? xs.filter(x => typeof x === 'string') : [])];
  const textKey = text => String(text || '').trim().toLocaleLowerCase('ru-RU').replace(/\s+/g, ' ').replace(/[.!?…]+$/g, '');
  const dateKey = (date = new Date()) => `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
  function previousDay(key) {
    const [y,m,d] = key.split('-').map(Number);
    return dateKey(new Date(y, m-1, d-1, 12));
  }
  function empty() {
    return { version: 3, revision: 0, custom: [], deleted: [], edits: {}, saved: [], haptics: true,
      days: {}, round: null, migrationNotice: false,
      game: { totalXp: 0, totalCards: 0, achievementCards: 0, streak: 0, lastGoalDate: '', cycles: 0, achievements: [] } };
  }
  function migrate(read, keys) {
    const state = empty();
    const json = (key, fallback) => { try { return JSON.parse(read(key)) ?? fallback; } catch { return fallback; } };
    const oldGame = json('affirm_game_state_v1', {});
    for (const field of ['totalXp','totalCards','achievementCards','streak','cycles']) state.game[field] = numeric(oldGame[field]);
    state.game.lastGoalDate = typeof oldGame.lastGoalDate === 'string' ? oldGame.lastGoalDate : '';
    state.game.achievements = unique(oldGame.achievements);
    state.custom = json('affirm_custom_v1', []);
    if (!Array.isArray(state.custom)) state.custom = [];
    state.custom = state.custom.filter(x => x && typeof x.id === 'string' && typeof x.text === 'string' && typeof x.theme === 'string');
    state.deleted = unique(json('affirm_deleted_v1', []));
    state.saved = unique(json('affirm_strong500_saved_v2', []));
    const edits = json('affirm_edits_v1', {});
    state.edits = edits && typeof edits === 'object' && !Array.isArray(edits) ? edits : {};
    state.haptics = !['0','false'].includes(read('affirm_haptics_v1'));
    for (const key of keys) {
      const match = /^affirm_daily_(time|cards)_v1:(\d{4}-\d{2}-\d{2})$/.exec(key);
      if (!match) continue;
      const day = getDay(state, match[2]);
      day[match[1] === 'time' ? 'timeMs' : 'cards'] = numeric(read(key));
    }
    if (oldGame.lastCycleGoalDate) getDay(state, oldGame.lastCycleGoalDate).completed = true;
    if (!read('affirm_game_state_v1')) {
      const today = getDay(state, dateKey());
      state.game.totalCards = today.cards;
      state.game.totalXp = today.cards;
    }
    // Old queues record preloading, not views. They cannot safely establish a completed round.
    // Keep all old keys untouched as a rollback copy; start a verified round and unique-day set.
    state.migrationNotice = keys.some(key => key.startsWith('affirm_'));
    return state;
  }
  function allItems(state, catalog) {
    const deleted = new Set(state.deleted);
    const base = catalog.items.map(item => {
      const edit = state.edits[item.id];
      return edit && typeof edit.text === 'string' && edit.text.trim() && Object.hasOwn(catalog.themes,edit.theme)
        ? { ...item, text: edit.text.trim(), theme: edit.theme, source: 'base', edited: true }
        : { ...item, source: 'base' };
    });
    const custom = state.custom.filter(x => x && typeof x.text === 'string' && x.text.trim() && Object.hasOwn(catalog.themes,x.theme))
      .map(x => ({ ...x, source: 'custom' }));
    return [...base, ...custom].filter(x => !deleted.has(x.id));
  }
  function activeItems(state, catalog) {
    const seen = new Set();
    return allItems(state, catalog).filter(item => {
      const key = textKey(item.text);
      if (!key || seen.has(key)) return false;
      seen.add(key); return true;
    });
  }
  function validateText(state, catalog, text, theme, excludeId) {
    if (typeof text !== 'string' || !text.trim()) throw new Error('Напиши текст аффирмации.');
    if (text.trim().length > 500) throw new Error('Максимум 500 символов.');
    if (!Object.hasOwn(catalog.themes,theme)) throw new Error('Выбери раздел.');
    if (allItems(state, catalog).some(x => x.id !== excludeId && textKey(x.text) === textKey(text))) {
      throw new Error('Такая аффирмация уже есть. Найди её через поиск.');
    }
  }
  function getDay(state, key) {
    return state.days[key] ||= { cards: 0, timeMs: 0, seen: [], completed: false };
  }
  function signature(items) { return items.map(x => x.id).sort().join(','); }
  function token() {
    return root.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }
  function ensureRound(state, catalog, random = Math.random) {
    const items = activeItems(state, catalog);
    const ids = items.map(x => x.id);
    const sig = signature(items);
    if (!ids.length) { state.round = null; return null; }
    if (state.round && state.round.signature === sig && !state.round.complete) return state.round;
    const lastId = state.round?.resumeId;
    for (let i=ids.length-1; i>0; i--) {
      const j = Math.floor(random() * (i+1)); [ids[i], ids[j]] = [ids[j], ids[i]];
    }
    if (ids.length > 1 && ids[0] === lastId) [ids[0],ids[1]] = [ids[1],ids[0]];
    state.round = { id: token(), signature: sig, order: ids, seen: [], resumeId: null, complete: false };
    return state.round;
  }
  function preview(state, catalog) {
    if (!state.round) return [];
    const byId = new Map(activeItems(state, catalog).map(x=>[x.id,x]));
    const seen = new Set(state.round.seen);
    const pending = state.round.order.filter(id => !seen.has(id));
    const ids = state.round.resumeId ? [state.round.resumeId, ...pending] : pending;
    return unique(ids).map(id => byId.get(id)).filter(Boolean);
  }
  function view(state, catalog, id, roundId, dayKey) {
    const rewards = [];
    const round = state.round;
    const items = activeItems(state, catalog);
    if (!round || round.id !== roundId || round.signature !== signature(items) || !items.some(x=>x.id===id)) return rewards;
    const day = getDay(state, dayKey);
    const game = state.game;
    const oldLevel = Math.floor(game.totalXp / 250) + 1;
    round.resumeId = id;
    const firstInDay = !day.seen.includes(id);
    if (firstInDay) day.seen.push(id);
    // Reloads, back-scrolls and another tab showing the same round/card cannot mint XP.
    const firstInRound = !round.seen.includes(id);
    if (firstInRound || firstInDay) {
      day.cards++; game.totalCards++; game.achievementCards++; game.totalXp++;
    }
    if (firstInRound) {
      round.seen.push(id);
      if (round.order.every(id => round.seen.includes(id)) && !round.complete) {
        round.complete = true; game.cycles++; game.totalXp += 100;
        rewards.push({ emoji: '🔄', title: 'Полный круг!', text: 'Вся колода просмотрена · +100 XP' });
      }
    }
    if (firstInDay && !day.completed && items.length && items.every(x => day.seen.includes(x.id))) {
      day.completed = true;
      if (game.lastGoalDate !== dayKey) {
        game.streak = game.lastGoalDate === previousDay(dayKey) ? game.streak+1 : 1;
        game.lastGoalDate = dayKey;
      }
      game.totalXp += 20;
      rewards.push({ emoji: '🎯', title: 'Цель дня выполнена!', text: `Все карты дня · +20 XP · 🔥 ${game.streak} дн.` });
    }
    const level = Math.floor(game.totalXp / 250) + 1;
    if (level > oldLevel) rewards.push({ emoji: '⭐', title: `Уровень ${level}`, text: `У тебя уже ${game.totalXp} XP.` });
    for (const [key, achieved, emoji, title] of milestones(game)) if (achieved && !game.achievements.includes(key)) {
      game.achievements.push(key); rewards.push({ emoji, title, text: 'Новое достижение!' });
    }
    return rewards;
  }
  function milestones(game) {
    const level = Math.floor(game.totalXp / 250) + 1;
    return [
      ['cards100', game.achievementCards>=100, '💯','100 карт'], ['cards500',game.achievementCards>=500,'🏅','500 карт'],
      ['cards1000',game.achievementCards>=1000,'🏆','1000 карт'], ['streak7',game.streak>=7,'🔥','7 дней подряд'],
      ['streak30',game.streak>=30,'🔥','30 дней подряд'], ['cycle1',game.cycles>=1,'🔄','Первый полный круг'],
      ['cycle10',game.cycles>=10,'👑','10 полных кругов'], ['level5',level>=5,'⭐','5 уровень'], ['level10',level>=10,'🌟','10 уровень']
    ];
  }
  function addTime(state, start, end) {
    // Split a short active interval at local midnight; never charge it all to yesterday.
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return;
    while (start < end) {
      const date = new Date(start);
      const midnight = new Date(date.getFullYear(), date.getMonth(), date.getDate()+1).getTime();
      const until = Math.min(midnight, end);
      getDay(state, dateKey(date)).timeMs += until-start;
      start = until;
    }
  }
  function toggleSaved(state, catalog, id) {
    if (!allItems(state, catalog).some(x => x.id === id)) return;
    state.saved = state.saved.includes(id) ? state.saved.filter(x=>x!==id) : [...state.saved,id];
  }
  function restoreBackup(input, catalog) {
    if (!input || input.version !== 3 || !Array.isArray(input.custom) || !Array.isArray(input.saved) ||
        !Array.isArray(input.deleted) || !input.edits || typeof input.edits !== 'object' || Array.isArray(input.edits) ||
        !input.days || typeof input.days !== 'object' || !input.game || typeof input.game !== 'object') {
      throw new Error('Это не резервная копия Affirm.');
    }
    const state = empty();
    const ids = new Set(catalog.items.map(x=>x.id));
    for (const item of input.custom) {
      if (!item || typeof item.id !== 'string' || ids.has(item.id) || typeof item.text !== 'string' || !item.text.trim() || item.text.length>500 || !Object.hasOwn(catalog.themes,item.theme)) throw new Error('В копии есть некорректные аффирмации.');
      ids.add(item.id); state.custom.push({id:item.id,text:item.text.trim(),theme:item.theme});
    }
    state.saved = unique(input.saved).filter(id=>ids.has(id));
    state.deleted = unique(input.deleted).filter(id=>ids.has(id));
    for (const [id,edit] of Object.entries(input.edits)) {
      if (!catalog.items.some(x=>x.id===id) || !edit || typeof edit.text!=='string' || !edit.text.trim() || edit.text.length>500 || !Object.hasOwn(catalog.themes,edit.theme)) throw new Error('В копии есть некорректные правки.');
      state.edits[id]={text:edit.text.trim(),theme:edit.theme};
    }
    for (const [key,day] of Object.entries(input.days)) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(key) || !day || typeof day!=='object') throw new Error('В копии некорректная статистика.');
      state.days[key]={cards:numeric(day.cards),timeMs:numeric(day.timeMs),seen:unique(day.seen),completed:day.completed===true};
    }
    for(const field of ['totalXp','totalCards','achievementCards','streak','cycles']) state.game[field]=numeric(input.game[field]);
    state.game.lastGoalDate = /^\d{4}-\d{2}-\d{2}$/.test(input.game.lastGoalDate) ? input.game.lastGoalDate : '';
    state.game.achievements = unique(input.game.achievements);
    state.haptics = input.haptics !== false;
    // A restored round needs valid IDs and a consistent seen subset. Otherwise restart it safely.
    const r=input.round; const active=activeItems(state,catalog); const activeIds=new Set(active.map(x=>x.id));
    if(r && typeof r.id==='string' && r.signature===signature(active) && Array.isArray(r.order) &&
       r.order.length===activeIds.size && new Set(r.order).size===activeIds.size && r.order.every(id=>activeIds.has(id)) &&
       Array.isArray(r.seen) && r.seen.every(id=>activeIds.has(id))) {
      state.round={id:r.id,signature:r.signature,order:[...r.order],seen:unique(r.seen),resumeId:activeIds.has(r.resumeId)?r.resumeId:null,complete:r.complete===true && activeIds.size>0 && unique(r.seen).length===activeIds.size};
    }
    return state;
  }
  const api = { empty, migrate, allItems, activeItems, validateText, textKey, dateKey, previousDay, getDay, ensureRound, preview, view, milestones, addTime, toggleSaved, restoreBackup, token };
  root.AffirmState = api;
  if (typeof module !== 'undefined') module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
