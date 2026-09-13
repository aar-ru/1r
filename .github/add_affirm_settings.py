from pathlib import Path
import re

p = Path('index.html')
s = p.read_text(encoding='utf-8')

# 1) Keep the built-in corpus separate from user customizations.
if 'const BASE_AFFIRMATIONS = [' not in s:
    if 'const AFFIRMATIONS = [' not in s:
        raise SystemExit('AFFIRMATIONS declaration not found')
    s = s.replace('const AFFIRMATIONS = [', 'const BASE_AFFIRMATIONS = [', 1)

marker_re = re.compile(r'(\n    \]\.map\(\(x, i\) => \(\{ id: `u\$\{i\+1\}`, theme: x\[0\], text: x\[1\] \}\)\);\n)')
if 'const CUSTOM_AFFIRMATIONS_KEY' not in s:
    m = marker_re.search(s)
    if not m:
        raise SystemExit('End of BASE_AFFIRMATIONS not found')
    customization = r'''

    const CUSTOM_AFFIRMATIONS_KEY = 'affirm_custom_v1';
    const DELETED_AFFIRMATIONS_KEY = 'affirm_deleted_v1';

    function readStoredJson(key, fallback) {
      try {
        const value = JSON.parse(localStorage.getItem(key));
        return value ?? fallback;
      } catch {
        return fallback;
      }
    }

    const deletedAffirmationIds = new Set((() => {
      const value = readStoredJson(DELETED_AFFIRMATIONS_KEY, []);
      return Array.isArray(value) ? value : [];
    })());

    const customAffirmations = (() => {
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
    const AFFIRMATIONS = effectiveAffirmations.length ? effectiveAffirmations : BASE_AFFIRMATIONS.slice(0, 1);
'''
    s = s[:m.end()] + customization + s[m.end():]

# 2) Add a settings button beside Saved.
old_css = '    .open-saved { justify-self: end; }\n'
new_css = '''    .top-actions { justify-self:end; display:flex; align-items:center; gap:8px; }\n    .open-saved { justify-self: end; }\n    .settings-link { text-decoration:none; font-size:18px; }\n'''
if '.top-actions {' not in s:
    if old_css not in s:
        raise SystemExit('open-saved CSS marker not found')
    s = s.replace(old_css, new_css, 1)

old_button = '''          <button class="icon-btn open-saved" aria-label="Открыть сохранённые">♡<span class="count-badge" ${saved.size ? '' : 'style="display:none"'}>${saved.size}</span></button>'''
new_button = '''          <div class="top-actions">
            <a class="icon-btn settings-link" href="settings.html" aria-label="Настройки">⚙</a>
            <button class="icon-btn open-saved" aria-label="Открыть сохранённые">♡<span class="count-badge" ${saved.size ? '' : 'style="display:none"'}>${saved.size}</span></button>
          </div>'''
if 'href="settings.html"' not in s:
    if old_button not in s:
        raise SystemExit('Saved button marker not found')
    s = s.replace(old_button, new_button, 1)

# 3) Remove favorites that point to affirmations hidden/deleted in Settings.
old_saved = "    let saved = new Set(JSON.parse(localStorage.getItem('affirm_strong500_saved_v2') || '[]'));\n"
new_saved = '''    const SAVED_KEY = 'affirm_strong500_saved_v2';
    let saved = new Set(JSON.parse(localStorage.getItem(SAVED_KEY) || '[]'));
    const activeAffirmationIds = new Set(AFFIRMATIONS.map(item => item.id));
    saved = new Set([...saved].filter(id => activeAffirmationIds.has(id)));
    localStorage.setItem(SAVED_KEY, JSON.stringify([...saved]));
'''
if 'const SAVED_KEY =' not in s:
    if old_saved not in s:
        raise SystemExit('Saved storage marker not found')
    s = s.replace(old_saved, new_saved, 1)

s = s.replace("localStorage.setItem('affirm_strong500_saved_v2', JSON.stringify([...saved]));", "localStorage.setItem(SAVED_KEY, JSON.stringify([...saved]));")

p.write_text(s, encoding='utf-8')
print('Settings integration installed')
