from pathlib import Path

OLD = """      const rawArray = after.slice(0, end + 1);\n      const rows = JSON.parse(rawArray);\n      return rows.map((x, i) => ({ id:`u${i+1}`, theme:x[0], text:x[1], source:'base' }));"""
NEW = """      const rawArray = after.slice(0, end + 1);\n      // JavaScript arrays may legally end with a trailing comma, but JSON.parse rejects it.\n      const normalizedArray = rawArray.replace(/,\\s*]/g, ']');\n      const rows = JSON.parse(normalizedArray);\n      return rows.map((x, i) => ({ id:`u${i+1}`, theme:x[0], text:x[1], source:'base' }));"""

paths = [
    Path('settings.html'),
    Path('.github/add_affirm_editing.py'),
]

changed = []
for path in paths:
    if not path.exists():
        continue
    src = path.read_text(encoding='utf-8')
    if NEW in src:
        continue
    if OLD not in src:
        raise SystemExit(f'Parser block not found in {path}')
    path.write_text(src.replace(OLD, NEW), encoding='utf-8')
    changed.append(str(path))

if not changed:
    print('Already fixed')
else:
    print('Fixed:', ', '.join(changed))
