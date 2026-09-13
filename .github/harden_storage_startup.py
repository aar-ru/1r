from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

old = """    function readStoredJson(key, fallback) {
      try {
        const value = JSON.parse(localStorage.getItem(key));
        return value ?? fallback;
      } catch {
        return fallback;
      }
    }
"""
new = """    function safeStorageGet(key) {
      try { return localStorage.getItem(key); } catch { return null; }
    }

    function safeStorageSet(key, value) {
      try { localStorage.setItem(key, value); return true; } catch { return false; }
    }

    function readStoredJson(key, fallback) {
      try {
        const raw = safeStorageGet(key);
        if (raw == null) return fallback;
        const value = JSON.parse(raw);
        return value ?? fallback;
      } catch {
        return fallback;
      }
    }
"""
if old not in s:
    raise SystemExit('readStoredJson block not found')
s = s.replace(old, new, 1)

repls = {
"    let saved = new Set(JSON.parse(localStorage.getItem(SAVED_KEY) || '[]'));": "    const savedStored = readStoredJson(SAVED_KEY, []);\n    let saved = new Set(Array.isArray(savedStored) ? savedStored : []);",
"    localStorage.setItem(SAVED_KEY, JSON.stringify([...saved]));": "    safeStorageSet(SAVED_KEY, JSON.stringify([...saved]));",
"    let dayElapsedMs = Number(localStorage.getItem(DAILY_TIME_PREFIX + dayKey) || 0);": "    let dayElapsedMs = Number(safeStorageGet(DAILY_TIME_PREFIX + dayKey) || 0);",
"      localStorage.setItem(DAILY_TIME_PREFIX + dayKey, String(Math.round(value)));": "      safeStorageSet(DAILY_TIME_PREFIX + dayKey, String(Math.round(value)));",
"      dayElapsedMs = Number(localStorage.getItem(DAILY_TIME_PREFIX + dayKey) || 0);": "      dayElapsedMs = Number(safeStorageGet(DAILY_TIME_PREFIX + dayKey) || 0);",
"      try { state = JSON.parse(localStorage.getItem(FAIR_QUEUE_KEY) || 'null'); } catch {}": "      try { state = JSON.parse(safeStorageGet(FAIR_QUEUE_KEY) || 'null'); } catch {}",
"        localStorage.setItem(FAIR_QUEUE_KEY, JSON.stringify({": "        safeStorageSet(FAIR_QUEUE_KEY, JSON.stringify({",
"        }));\n      } catch {}\n    }\n\n    function nextItem()": "        }));\n      } catch {}\n    }\n\n    function nextItem()",
}
for a,b in repls.items():
    if a not in s:
        print('warning missing:', a[:70])
    else:
        s = s.replace(a,b,1)

# There is a second saved write inside toggleSave; harden every remaining exact saved write.
s = s.replace("      localStorage.setItem(SAVED_KEY, JSON.stringify([...saved]));", "      safeStorageSet(SAVED_KEY, JSON.stringify([...saved]));")

p.write_text(s, encoding='utf-8')
print('Hardened startup storage access')
