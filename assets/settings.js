(async function () {
  'use strict';
  const Core=window.AffirmState, Store=window.AffirmStore, Catalog=window.AffirmCatalog;
  const $=id=>document.getElementById(id);
  const list=$('list'), notice=$('notice'), editBackdrop=$('editBackdrop');
  let state, editingId=null, previousFocus, undoId=null, busy=false;
  function showNotice(text) { notice.textContent=text; notice.classList.add('show'); }
  function render() {
    if(!state) return;
    $('hapticsToggle').checked=state.haptics;
    const items=Core.allItems(state,Catalog);
    $('activeCount').textContent=Core.activeItems(state,Catalog).length;
    $('customCount').textContent=state.custom.length;
    $('editedCount').textContent=Object.keys(state.edits).length;
    $('deletedCount').textContent=state.deleted.length;
    $('restoreBtn').disabled=!state.deleted.length;
    $('resetEditsBtn').disabled=!Object.keys(state.edits).length;
    $('undoDelete').hidden=!undoId;
    const query=$('search').value.trim().toLocaleLowerCase('ru-RU'), theme=$('filterTheme').value;
    const filtered=items.filter(x=>(theme==='all'||x.theme===theme) && x.text.toLocaleLowerCase('ru-RU').includes(query));
    list.replaceChildren();
    if(!filtered.length) { const empty=document.createElement('div'); empty.className='empty'; empty.textContent='Ничего не найдено.'; list.appendChild(empty); }
    for(const item of filtered) {
      const row=document.createElement('div'); row.className='item';
      const main=document.createElement('div'), text=document.createElement('div'); text.className='item-text'; text.textContent=item.text;
      const meta=document.createElement('div'); meta.className='meta';
      for(const label of [Catalog.themes[item.theme].label,item.source==='custom'?'добавлено мной':null,item.edited?'изменено':null].filter(Boolean)) {
        const tag=document.createElement('span'); tag.className='tag'; tag.textContent=label; meta.appendChild(tag);
      }
      main.append(text,meta);
      const controls=document.createElement('div'); controls.className='item-actions';
      const edit=document.createElement('button'); edit.type='button'; edit.className='edit'; edit.textContent='✎'; edit.setAttribute('aria-label','Редактировать аффирмацию');
      edit.addEventListener('click',()=>openEdit(item));
      const del=document.createElement('button'); del.type='button'; del.className='delete'; del.textContent='×'; del.setAttribute('aria-label','Удалить аффирмацию');
      del.addEventListener('click',async()=>{
        if(await change(s=>{ if(!s.deleted.includes(item.id)) s.deleted.push(item.id); },'Удалено. Можно отменить или восстановить в настройках.')) {
          undoId=item.id; render();
        }
      });
      controls.append(edit,del); row.append(main,controls); list.appendChild(row);
    }
  }
  async function change(fn,success) {
    if(busy) return false;
    busy=true;
    try { const update=await Store.transaction(fn); state=update.state; render(); if(success) showNotice(success); return true; }
    catch(error) {showNotice(error.message);return false;}
    finally {busy=false;}
  }
  function openEdit(item) {
    editingId=item.id; previousFocus=document.activeElement; $('editError').textContent='';
    $('editText').value=item.text; $('editTheme').value=item.theme;
    editBackdrop.classList.add('open'); document.querySelector('main').inert=true; document.body.style.overflow='hidden'; $('editText').focus();
  }
  function closeEdit() {
    editingId=null; editBackdrop.classList.remove('open'); document.querySelector('main').inert=false; document.body.style.overflow='';
    if(previousFocus?.isConnected) previousFocus.focus(); else $('search').focus();
  }
  async function saveEdit() {
    if(!editingId) return;
    const id=editingId, text=$('editText').value.trim(), theme=$('editTheme').value;
    const saved=await change(s=>{
      const current=Core.allItems(s,Catalog).find(x=>x.id===id);
      if(!current) throw new Error('Аффирмация удалена в другой вкладке.');
      // Existing duplicates remain editable; unchanged text may retain its original category.
      if(Core.textKey(current.text)!==Core.textKey(text)) Core.validateText(s,Catalog,text,theme,id);
      else if(!text || text.length>500 || !Catalog.themes[theme]) throw new Error('Проверь текст и раздел.');
      if(current.source==='custom') { const index=s.custom.findIndex(x=>x.id===id); s.custom[index]={id,text,theme}; }
      else {
        const original=Catalog.items.find(x=>x.id===id);
        if(original.text===text && original.theme===theme) delete s.edits[id];
        else s.edits[id]={text,theme};
      }
    },'Изменения сохранены.');
    if(saved) closeEdit();
    else $('editError').textContent=notice.textContent;
  }
  for(const [value,theme] of Object.entries(Catalog.themes)) {
    for(const id of ['newTheme','editTheme','filterTheme']) { const option=document.createElement('option'); option.value=value; option.textContent=theme.label; $(id).appendChild(option); }
  }
  $('addBtn').addEventListener('click',async()=>{
    const text=$('newText').value.trim(),theme=$('newTheme').value;
    if(await change(s=>{Core.validateText(s,Catalog,text,theme);s.custom.push({id:`c-${Core.token()}`,text,theme});},'Добавлено в ленту.')) $('newText').value='';
  });
  $('hapticsToggle').addEventListener('change',async()=>{
    const checked=$('hapticsToggle').checked;
    if(!await change(s=>{s.haptics=checked;})) render();
  });
  $('restoreBtn').addEventListener('click',()=>change(s=>{s.deleted=[];undoId=null;},'Удалённые аффирмации восстановлены.'));
  $('undoDelete').addEventListener('click',async()=>{
    const id=undoId;
    if(await change(s=>{s.deleted=s.deleted.filter(x=>x!==id);},'Удаление отменено.')) {undoId=null;render();}
  });
  $('resetEditsBtn').addEventListener('click',()=>{
    if(confirm('Сбросить все правки стандартных аффирмаций?')) change(s=>{s.edits={};},'Правки сброшены.');
  });
  $('saveEdit').addEventListener('click',saveEdit);
  $('cancelEdit').addEventListener('click',closeEdit); $('closeEdit').addEventListener('click',closeEdit);
  editBackdrop.addEventListener('click',e=>{if(e.target===editBackdrop) closeEdit();});
  document.addEventListener('keydown',e=>{
    if(!editingId) return;
    if(e.key==='Escape') closeEdit();
    if(e.key==='Tab') {
      const controls=[...editBackdrop.querySelectorAll('button,textarea,select')];
      if(e.shiftKey && document.activeElement===controls[0]) {e.preventDefault();controls.at(-1).focus();}
      else if(!e.shiftKey && document.activeElement===controls.at(-1)) {e.preventDefault();controls[0].focus();}
    }
  });
  $('search').addEventListener('input',render); $('filterTheme').addEventListener('change',render);
  $('exportBtn').addEventListener('click',async()=>{
    try {
      const backup=await Store.read();
      const url=URL.createObjectURL(new Blob([JSON.stringify(backup,null,2)],{type:'application/json'}));
      const link=document.createElement('a'); link.href=url; link.download=`affirm-${Core.dateKey()}.json`; link.click();
      setTimeout(()=>URL.revokeObjectURL(url),1000); showNotice('Резервная копия подготовлена.');
    } catch(error) {showNotice(error.message);}
  });
  $('importFile').addEventListener('change',async e=>{
    const file=e.target.files[0]; if(!file) return;
    try {
      if(file.size>5*1024*1024) throw new Error('Файл слишком большой. Максимум 5 МБ.');
      const restored=Core.restoreBackup(JSON.parse(await file.text()),Catalog);
      if(confirm('Заменить текущие аффирмации, избранное и прогресс данными из резервной копии?')) {
        await change(s=>{const revision=s.revision;Object.assign(s,restored,{revision});},'Данные восстановлены.');
      }
    } catch(error) {showNotice(error instanceof SyntaxError?'Не удалось прочитать JSON-файл.':error.message);}
    finally {e.target.value='';}
  });
  Store.subscribe(next=>{if(!state || next.revision>=state.revision){state=next;render();}});
  window.addEventListener('affirm-error',e=>showNotice(e.detail));
  try {
    // Persist the migration before the first edit; two simultaneously opened pages share it.
    const update=await Store.transaction(()=>{}); state=update.state; render();
    $('storageWarning').hidden=!Store.temporary;
  } catch(error) {showNotice(error.message);list.textContent='Не удалось открыть данные. Обнови страницу.';}
})();
