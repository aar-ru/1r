from pathlib import Path

# ---- Patch index.html so local edits affect the feed ----
p = Path('index.html')
s = p.read_text(encoding='utf-8')

old = """    const CUSTOM_AFFIRMATIONS_KEY = 'affirm_custom_v1';
    const DELETED_AFFIRMATIONS_KEY = 'affirm_deleted_v1';
"""
new = """    const CUSTOM_AFFIRMATIONS_KEY = 'affirm_custom_v1';
    const DELETED_AFFIRMATIONS_KEY = 'affirm_deleted_v1';
    const EDITED_AFFIRMATIONS_KEY = 'affirm_edits_v1';
"""
if old not in s:
    raise SystemExit('index constants marker not found')
s = s.replace(old, new, 1)

old = """    const customAffirmations = (() => {
      const value = readStoredJson(CUSTOM_AFFIRMATIONS_KEY, []);
      if (!Array.isArray(value)) return [];
      return value.filter(item =>
        item && typeof item.id === 'string' && typeof item.text === 'string' &&
        item.text.trim() && THEMES[item.theme]
      ).map(item => ({ id:item.id, theme:item.theme, text:item.text.trim() }));
    })();

    const effectiveAffirmations = [
      ...BASE_AFFIRMATIONS.filter(item => !deletedAffirmationIds.has(item.id)),
      ...customAffirmations.filter(item => !deletedAffirmationIds.has(item.id))
    ];
"""
new = """    const customAffirmations = (() => {
      const value = readStoredJson(CUSTOM_AFFIRMATIONS_KEY, []);
      if (!Array.isArray(value)) return [];
      return value.filter(item =>
        item && typeof item.id === 'string' && typeof item.text === 'string' &&
        item.text.trim() && THEMES[item.theme]
      ).map(item => ({ id:item.id, theme:item.theme, text:item.text.trim() }));
    })();

    const editedAffirmations = (() => {
      const value = readStoredJson(EDITED_AFFIRMATIONS_KEY, {});
      return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
    })();

    const editedBaseAffirmations = BASE_AFFIRMATIONS.map(item => {
      const edit = editedAffirmations[item.id];
      if (!edit || typeof edit.text !== 'string' || !edit.text.trim() || !THEMES[edit.theme]) return item;
      return { ...item, text:edit.text.trim(), theme:edit.theme };
    });

    const effectiveAffirmations = [
      ...editedBaseAffirmations.filter(item => !deletedAffirmationIds.has(item.id)),
      ...customAffirmations.filter(item => !deletedAffirmationIds.has(item.id))
    ];
"""
if old not in s:
    raise SystemExit('index effective affirmations marker not found')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')

# ---- Patch settings.html ----
p = Path('settings.html')
s = p.read_text(encoding='utf-8')

old = """    .delete { width:42px; height:42px; border-radius:50%; border:1px solid rgba(255,105,105,.25); background:rgba(255,105,105,.08); color:#ff9292; cursor:pointer; display:grid; place-items:center; font-size:18px; }
    .secondary { border:1px solid var(--line); border-radius:14px; padding:11px 13px; background:#171717; color:#fff; font-weight:700; cursor:pointer; }
"""
new = """    .item-actions { display:flex; gap:7px; align-items:center; }
    .edit,.delete { width:42px; height:42px; border-radius:50%; cursor:pointer; display:grid; place-items:center; font-size:18px; }
    .edit { border:1px solid var(--line); background:#1c1c1c; color:#fff; }
    .delete { border:1px solid rgba(255,105,105,.25); background:rgba(255,105,105,.08); color:#ff9292; }
    .edited-tag { color:#b8dcff; }
    .secondary { border:1px solid var(--line); border-radius:14px; padding:11px 13px; background:#171717; color:#fff; font-weight:700; cursor:pointer; }
    .edit-backdrop { position:fixed; inset:0; z-index:40; background:rgba(0,0,0,.72); display:none; align-items:flex-end; justify-content:center; }
    .edit-backdrop.open { display:flex; }
    .edit-sheet { width:min(720px,100%); max-height:86dvh; overflow:auto; background:#111; border:1px solid var(--line); border-radius:28px 28px 0 0; padding:20px 16px max(24px,calc(env(safe-area-inset-bottom) + 16px)); box-shadow:0 -30px 80px rgba(0,0,0,.45); }
    .edit-head { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:16px; }
    .edit-head h2 { margin:0; font-size:22px; }
    .edit-actions { display:grid; grid-template-columns:1fr 1fr; gap:9px; }
"""
if old not in s:
    raise SystemExit('settings css marker not found')
s = s.replace(old, new, 1)

old = """        <div class=\"pill\">Добавлено: <strong id=\"customCount\">—</strong></div>
        <div class=\"pill\">Удалено: <strong id=\"deletedCount\">—</strong></div>
"""
new = """        <div class=\"pill\">Добавлено: <strong id=\"customCount\">—</strong></div>
        <div class=\"pill\">Изменено: <strong id=\"editedCount\">—</strong></div>
        <div class=\"pill\">Удалено: <strong id=\"deletedCount\">—</strong></div>
"""
if old not in s:
    raise SystemExit('settings stats marker not found')
s = s.replace(old, new, 1)

old = """      <div class=\"actions\" style=\"margin-bottom:12px\">
        <button class=\"secondary\" id=\"restoreBtn\">Вернуть удалённые</button>
      </div>
"""
new = """      <div class=\"actions\" style=\"margin-bottom:12px\">
        <button class=\"secondary\" id=\"restoreBtn\">Вернуть удалённые</button>
        <button class=\"secondary\" id=\"resetEditsBtn\">Сбросить правки</button>
      </div>
"""
if old not in s:
    raise SystemExit('settings actions marker not found')
s = s.replace(old, new, 1)

old = """  </main>

  <script>
"""
new = """  </main>

  <div class=\"edit-backdrop\" id=\"editBackdrop\" role=\"dialog\" aria-modal=\"true\" aria-labelledby=\"editTitle\">
    <div class=\"edit-sheet\">
      <div class=\"edit-head\">
        <h2 id=\"editTitle\">Редактировать</h2>
        <button class=\"back\" id=\"closeEdit\" type=\"button\" aria-label=\"Закрыть\">×</button>
      </div>
      <div class=\"field\">
        <label for=\"editText\">Текст</label>
        <textarea id=\"editText\" maxlength=\"500\"></textarea>
      </div>
      <div class=\"field\">
        <label for=\"editTheme\">Раздел</label>
        <select id=\"editTheme\"></select>
      </div>
      <div class=\"edit-actions\">
        <button class=\"secondary\" id=\"cancelEdit\" type=\"button\">Отмена</button>
        <button class=\"primary\" id=\"saveEdit\" type=\"button\">Сохранить</button>
      </div>
    </div>
  </div>

  <script>
"""
if old not in s:
    raise SystemExit('settings modal insertion marker not found')
s = s.replace(old, new, 1)

old = """    const CUSTOM_KEY = 'affirm_custom_v1';
    const DELETED_KEY = 'affirm_deleted_v1';
    const SAVED_KEY = 'affirm_strong500_saved_v2';
"""
new = """    const CUSTOM_KEY = 'affirm_custom_v1';
    const DELETED_KEY = 'affirm_deleted_v1';
    const EDITED_KEY = 'affirm_edits_v1';
    const SAVED_KEY = 'affirm_strong500_saved_v2';
"""
if old not in s:
    raise SystemExit('settings constants marker not found')
s = s.replace(old, new, 1)

old = """    const notice = document.getElementById('notice');
    let base = [];
"""
new = """    const notice = document.getElementById('notice');
    const editBackdrop = document.getElementById('editBackdrop');
    const editText = document.getElementById('editText');
    const editTheme = document.getElementById('editTheme');
    let base = [];
    let editingItem = null;
"""
if old not in s:
    raise SystemExit('settings element marker not found')
s = s.replace(old, new, 1)

old = """    function saveCustom(items) { localStorage.setItem(CUSTOM_KEY, JSON.stringify(items)); }
    function saveDeleted(set) { localStorage.setItem(DELETED_KEY, JSON.stringify([...set])); }
"""
new = """    function editedItems() {
      const edits = loadJson(EDITED_KEY, {});
      return edits && typeof edits === 'object' && !Array.isArray(edits) ? edits : {};
    }

    function saveCustom(items) { localStorage.setItem(CUSTOM_KEY, JSON.stringify(items)); }
    function saveDeleted(set) { localStorage.setItem(DELETED_KEY, JSON.stringify([...set])); }
    function saveEdits(edits) { localStorage.setItem(EDITED_KEY, JSON.stringify(edits)); }
"""
if old not in s:
    raise SystemExit('settings save funcs marker not found')
s = s.replace(old, new, 1)

old = """    function allActive() {
      const deleted = deletedIds();
      const custom = customItems().map(x => ({...x, source:'custom'}));
      return [...base.filter(x => !deleted.has(x.id)), ...custom.filter(x => !deleted.has(x.id))];
    }
"""
new = """    function allActive() {
      const deleted = deletedIds();
      const edits = editedItems();
      const editedBase = base.map(item => {
        const edit = edits[item.id];
        return edit && edit.text && THEME_LABELS[edit.theme]
          ? { ...item, text:edit.text, theme:edit.theme, edited:true }
          : item;
      });
      const custom = customItems().map(x => ({...x, source:'custom'}));
      return [...editedBase.filter(x => !deleted.has(x.id)), ...custom.filter(x => !deleted.has(x.id))];
    }
"""
if old not in s:
    raise SystemExit('settings allActive marker not found')
s = s.replace(old, new, 1)

old = """      document.getElementById('customCount').textContent = custom.length;
      document.getElementById('deletedCount').textContent = [...deleted].filter(id => base.some(x => x.id === id)).length;
      document.getElementById('restoreBtn').disabled = deleted.size === 0;
"""
new = """      const edits = editedItems();
      document.getElementById('customCount').textContent = custom.length;
      document.getElementById('editedCount').textContent = Object.keys(edits).filter(id => base.some(x => x.id === id)).length;
      document.getElementById('deletedCount').textContent = [...deleted].filter(id => base.some(x => x.id === id)).length;
      document.getElementById('restoreBtn').disabled = deleted.size === 0;
      document.getElementById('resetEditsBtn').disabled = Object.keys(edits).length === 0;
"""
if old not in s:
    raise SystemExit('settings stats logic marker not found')
s = s.replace(old, new, 1)

old = """        if (item.source === 'custom') {
          const customTag = document.createElement('span');
          customTag.className = 'tag custom-tag';
          customTag.textContent = 'добавлено мной';
          meta.appendChild(customTag);
        }
        main.append(text, meta);

        const del = document.createElement('button');
        del.className = 'delete';
        del.type = 'button';
        del.setAttribute('aria-label', 'Удалить аффирмацию');
        del.textContent = '×';
        del.addEventListener('click', () => deleteItem(item));
        row.append(main, del);
"""
new = """        if (item.source === 'custom') {
          const customTag = document.createElement('span');
          customTag.className = 'tag custom-tag';
          customTag.textContent = 'добавлено мной';
          meta.appendChild(customTag);
        }
        if (item.edited) {
          const editedTag = document.createElement('span');
          editedTag.className = 'tag edited-tag';
          editedTag.textContent = 'изменено';
          meta.appendChild(editedTag);
        }
        main.append(text, meta);

        const controls = document.createElement('div');
        controls.className = 'item-actions';
        const edit = document.createElement('button');
        edit.className = 'edit';
        edit.type = 'button';
        edit.setAttribute('aria-label', 'Редактировать аффирмацию');
        edit.textContent = '✎';
        edit.addEventListener('click', () => openEdit(item));

        const del = document.createElement('button');
        del.className = 'delete';
        del.type = 'button';
        del.setAttribute('aria-label', 'Удалить аффирмацию');
        del.textContent = '×';
        del.addEventListener('click', () => deleteItem(item));
        controls.append(edit, del);
        row.append(main, controls);
"""
if old not in s:
    raise SystemExit('settings render controls marker not found')
s = s.replace(old, new, 1)

old = """    function deleteItem(item) {
"""
new = """    function openEdit(item) {
      editingItem = item;
      editText.value = item.text;
      editTheme.value = item.theme;
      editBackdrop.classList.add('open');
      document.body.style.overflow = 'hidden';
      setTimeout(() => editText.focus(), 50);
    }

    function closeEdit() {
      editingItem = null;
      editBackdrop.classList.remove('open');
      document.body.style.overflow = '';
    }

    function saveCurrentEdit() {
      if (!editingItem) return;
      const text = editText.value.trim();
      const theme = editTheme.value;
      if (!text) { showNotice('Текст аффирмации пустой.'); return; }
      if (!THEME_LABELS[theme]) return;

      if (editingItem.source === 'custom') {
        const items = customItems();
        const index = items.findIndex(x => x.id === editingItem.id);
        if (index >= 0) items[index] = { ...items[index], text, theme };
        saveCustom(items);
      } else {
        const edits = editedItems();
        const original = base.find(x => x.id === editingItem.id);
        if (original && original.text === text && original.theme === theme) delete edits[editingItem.id];
        else edits[editingItem.id] = { text, theme };
        saveEdits(edits);
      }
      closeEdit();
      showNotice('Изменения сохранены.');
      render();
    }

    function deleteItem(item) {
"""
if old not in s:
    raise SystemExit('settings edit funcs insertion marker not found')
s = s.replace(old, new, 1)

old = """    document.getElementById('restoreBtn').addEventListener('click', () => {
      localStorage.removeItem(DELETED_KEY);
      showNotice('Все стандартные аффирмации восстановлены.');
      render();
    });

    search.addEventListener('input', render);
"""
new = """    document.getElementById('restoreBtn').addEventListener('click', () => {
      localStorage.removeItem(DELETED_KEY);
      showNotice('Все стандартные аффирмации восстановлены.');
      render();
    });

    document.getElementById('resetEditsBtn').addEventListener('click', () => {
      localStorage.removeItem(EDITED_KEY);
      showNotice('Правки стандартных аффирмаций сброшены.');
      render();
    });

    document.getElementById('saveEdit').addEventListener('click', saveCurrentEdit);
    document.getElementById('cancelEdit').addEventListener('click', closeEdit);
    document.getElementById('closeEdit').addEventListener('click', closeEdit);
    editBackdrop.addEventListener('click', (e) => { if (e.target === editBackdrop) closeEdit(); });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && editBackdrop.classList.contains('open')) closeEdit();
    });

    search.addEventListener('input', render);
"""
if old not in s:
    raise SystemExit('settings event marker not found')
s = s.replace(old, new, 1)

old = """        const a = document.createElement('option'); a.value = value; a.textContent = label; newTheme.appendChild(a);
        const b = document.createElement('option'); b.value = value; b.textContent = label; filterTheme.appendChild(b);
"""
new = """        const a = document.createElement('option'); a.value = value; a.textContent = label; newTheme.appendChild(a);
        const b = document.createElement('option'); b.value = value; b.textContent = label; filterTheme.appendChild(b);
        const c = document.createElement('option'); c.value = value; c.textContent = label; editTheme.appendChild(c);
"""
if old not in s:
    raise SystemExit('settings theme options marker not found')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('Editing support installed')
