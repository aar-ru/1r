from pathlib import Path

OLD = """      const rawArray = after.slice(0, end + 1);\n      const rows = JSON.parse(rawArray);\n      return rows.map((x, i) => ({ id:`u${i+1}`, theme:x[0], text:x[1], source:'base' }));"""
NEW = """      const rawArray = after.slice(0, end + 1);\n      // JavaScript arrays may legally end with a trailing comma, but JSON.parse rejects it.\n      const normalizedArray = rawArray.replace(/,\\s*]/g, ']');\n      const rows = JSON.parse(normalizedArray);\n      return rows.map((x, i) => ({ id:`u${i+1}`, theme:x[0], text:x[1], source:'base' }));"""

path = Path('settings.html')
src = path.read_text(encoding='utf-8')
if NEW in src:
    print('settings.html already fixed')
elif OLD in src:
    path.write_text(src.replace(OLD, NEW), encoding='utf-8')
    print('Fixed settings.html parser')
else:
    raise SystemExit('Parser block not found in settings.html')
