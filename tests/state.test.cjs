const test = require('node:test');
const assert = require('node:assert/strict');
const Core = require('../assets/state.js');
const catalog = { themes: { self: { label:'Я',images:['test.jpg'] } }, items: [1,2,3].map(n=>({id:`u${n}`,theme:'self',text:`Текст ${n}`})) };
const day='2026-09-17';

test('preloading and reopening never consume unread cards or award a round',()=>{
  const s=Core.empty(); Core.ensureRound(s,catalog);
  const id=s.round.order[0], round=s.round.id;
  for(let n=0;n<40;n++) {
    assert.equal(Core.preview(s,catalog).length,3);
    Core.view(s,catalog,id,round,day);
    assert.equal(Core.ensureRound(s,catalog).id,round);
  }
  assert.deepEqual(s.round.seen,[id]); assert.equal(s.game.totalCards,1);
  assert.equal(s.game.totalXp,1); assert.equal(s.game.cycles,0); assert.equal(s.days[day].completed,false);
});
test('only unique actual views complete a round, with exactly one cycle and daily bonus',()=>{
  const s=Core.empty(); Core.ensureRound(s,catalog);
  const ids=[...s.round.order], round=s.round.id;
  Core.view(s,catalog,ids[2],round,day);
  assert.equal(s.game.cycles,0,'the last preloaded card is not proof of reading the others');
  Core.view(s,catalog,ids[0],round,day); Core.view(s,catalog,ids[1],round,day);
  assert.equal(s.game.cycles,1); assert.equal(s.game.totalXp,123); assert.equal(s.days[day].completed,true);
  Core.view(s,catalog,ids[1],round,day); assert.equal(s.game.totalXp,123);
  Core.ensureRound(s,catalog); Core.view(s,catalog,ids[1],round,day);
  assert.equal(s.game.totalXp,123,'stale previous-round callbacks are ignored');
  const second=s.round.id;
  for(const id of s.round.order) Core.view(s,catalog,id,second,day);
  assert.equal(s.game.totalXp,226); assert.equal(s.game.cycles,2); assert.equal(s.game.streak,1);
});
test('changing the active deck cannot accidentally finish a previous round',()=>{
  const s=Core.empty(); Core.ensureRound(s,catalog); const round=s.round.id;
  Core.view(s,catalog,'u1',round,day); s.deleted.push('u2');
  Core.view(s,catalog,'u3',round,day); assert.equal(s.game.cycles,0);
  Core.ensureRound(s,catalog); assert.notEqual(s.round.id,round); assert.equal(s.round.seen.length,0);
});
test('all deleted means a genuinely empty feed and no XP or daily goal',()=>{
  const s=Core.empty(); s.deleted=catalog.items.map(x=>x.id);
  assert.deepEqual(Core.activeItems(s,catalog),[]); assert.equal(Core.ensureRound(s,catalog),null);
  assert.deepEqual(Core.preview(s,catalog),[]); Core.view(s,catalog,'u1','anything',day);
  assert.equal(s.game.totalXp,0); assert.equal(s.game.cycles,0);
});
test('duplicates are rejected on input, while old duplicates remain manageable',()=>{
  const s=Core.empty(); s.custom.push({id:'c1',theme:'self',text:'Текст 1'});
  assert.equal(Core.allItems(s,catalog).length,4); assert.equal(Core.activeItems(s,catalog).length,3);
  assert.throws(()=>Core.validateText(s,catalog,' ТЕКСТ 1! ','self'),/уже есть/);
  assert.throws(()=>Core.validateText(s,catalog,'','self'),/Напиши/);
});
test('migration preserves existing saved IDs, custom text, edits, XP, time and completed goals',()=>{
  const map=new Map([
    ['affirm_custom_v1',JSON.stringify([{id:'c1',theme:'self',text:'Свой текст'}])],
    ['affirm_edits_v1',JSON.stringify({u2:{theme:'self',text:'Правка'}})],
    ['affirm_strong500_saved_v2','["u2","c1"]'],['affirm_deleted_v1','["u3"]'],
    ['affirm_game_state_v1',JSON.stringify({totalXp:1234,totalCards:500,achievementCards:100,cycles:2,streak:7,lastGoalDate:day,lastCycleGoalDate:day,achievements:['cards100']})],
    [`affirm_daily_cards_v1:${day}`,'100'],[`affirm_daily_time_v1:${day}`,'12345'],['affirm_fair_queue_v1','{"remaining":["u3"]}']
  ]);
  const s=Core.migrate(k=>map.get(k)??null,[...map.keys()]);
  assert.equal(s.game.totalXp,1234); assert.deepEqual(s.saved,['u2','c1']); assert.equal(s.custom[0].text,'Свой текст');
  assert.equal(s.edits.u2.text,'Правка'); assert.equal(s.days[day].cards,100); assert.equal(s.days[day].timeMs,12345);
  assert.equal(s.days[day].completed,true); assert.equal(s.round,null); assert.equal(map.has('affirm_fair_queue_v1'),true);
});
test('active time is additive and split correctly at local midnight',()=>{
  const s=Core.empty(), start=new Date(2026,8,17,23,59,59).getTime();
  Core.addTime(s,start,start+2000); Core.addTime(s,start+2000,start+3000);
  assert.equal(s.days[day].timeMs,1000); assert.equal(s.days['2026-09-18'].timeMs,2000);
});
test('a new day starts a fresh unique-day goal without clearing history',()=>{
  const s=Core.empty(); Core.ensureRound(s,catalog);
  const id=s.round.order[0]; Core.view(s,catalog,id,s.round.id,day);
  Core.view(s,catalog,id,s.round.id,'2026-09-18');
  assert.deepEqual(s.days['2026-09-18'].seen,[id]); assert.equal(s.days[day].cards,1);
  assert.equal(s.game.totalXp,2,'a new day credits the first actual view on that day');
  assert.equal(s.days['2026-09-18'].cards,1);
});
test('backup round trip preserves data and rejects malformed input',()=>{
  const s=Core.empty(); Core.ensureRound(s,catalog); Core.view(s,catalog,'u1',s.round.id,day);
  s.saved=['u1']; s.custom=[{id:'c1',theme:'self',text:'Свой текст'}]; s.deleted=['u2'];
  Core.ensureRound(s,catalog);
  assert.deepEqual(Core.restoreBackup(JSON.parse(JSON.stringify(s)),catalog),s);
  assert.throws(()=>Core.restoreBackup({version:3},catalog),/копия/);
  assert.throws(()=>Core.restoreBackup({...s,custom:[{id:'u1',theme:'self',text:'bad'}]},catalog),/некорректные/);
  assert.throws(()=>Core.restoreBackup({...s,custom:[{id:'c2',theme:'__proto__',text:'bad'}]},catalog),/некорректные/);
});

test('round summary includes only this round time and XP and survives reopening and backup',()=>{
  const s=Core.empty();s.game.totalXp=500;
  Core.addTime(s,1000,61000);Core.ensureRound(s,catalog);
  const round=s.round.id;
  for(const id of s.round.order) { Core.addTime(s,61000,91000);Core.view(s,catalog,id,round,day); }
  assert.equal(s.round.summary.number,1);assert.equal(s.round.summary.cards,3);
  assert.equal(s.round.summary.timeMs,90000);assert.equal(s.round.summary.xp,123);
  assert.equal(s.round.summary.fullStats,true);
  const summary=structuredClone(s.round.summary);
  Core.addTime(s,100000,110000);Core.view(s,catalog,s.round.resumeId,round,'2026-09-18');
  assert.deepEqual(s.round.summary,summary);assert.equal(s.game.totalXp,623);
  Core.ensureRound(s,catalog,Math.random,false);assert.equal(s.round.id,round);
  assert.deepEqual(Core.restoreBackup(JSON.parse(JSON.stringify(s)),catalog),s);
  Core.ensureRound(s,catalog);assert.notEqual(s.round.id,round);
  for(const id of s.round.order)Core.view(s,catalog,id,s.round.id,day);
  assert.equal(s.round.summary.number,2);assert.equal(s.round.summary.xp,103);
  assert.equal(s.round.summary.timeMs,0);assert.equal(s.game.streak,1);
});
test('existing rounds finish without reset and distinguish legacy totals from full round statistics',()=>{
  const s=Core.empty();Core.ensureRound(s,catalog);delete s.round.stats;
  const round=s.round.id;Core.view(s,catalog,s.round.order[0],round,day);
  assert.equal(Core.ensureRound(s,catalog,Math.random,false).id,round);
  Core.getDay(s,day).timeMs=120000;
  for(const id of s.round.order)Core.view(s,catalog,id,round,day);
  assert.equal(s.round.summary.fullStats,false);assert.equal(s.round.summary.timeMs,120000);
  assert.equal(s.round.summary.xp,100);assert.equal(s.game.totalXp,123);
  assert.equal(s.round.summary.cards,3);
});
test('round totals span midnight while daily goal bonuses remain once per date',()=>{
  const s=Core.empty();Core.ensureRound(s,catalog);
  const round=s.round.id,ids=s.round.order;
  const midnight=new Date(2026,8,18).getTime();
  Core.view(s,catalog,ids[0],round,day);Core.addTime(s,midnight-1000,midnight+2000);
  for(const id of ids)Core.view(s,catalog,id,round,'2026-09-18');
  assert.equal(s.round.summary.timeMs,3000);assert.equal(s.round.summary.xp,124);
  assert.equal(s.days[day].completed,false);assert.equal(s.days['2026-09-18'].completed,true);
});
