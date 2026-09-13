from pathlib import Path

# Fix the missing comma between the old corpus and screenshot additions.
p = Path('index.html')
src = p.read_text(encoding='utf-8')
old = '      ["fulfilled","Яне ни с кем больше не интересно."]\n      ["calm","Моё спокойствие растёт вместе с моей уверенностью в себе."],'
new = '      ["fulfilled","Яне ни с кем больше не интересно."],\n      ["calm","Моё спокойствие растёт вместе с моей уверенностью в себе."],'
if old not in src:
    raise SystemExit('Broken boundary not found in index.html')
src = src.replace(old, new, 1)
p.write_text(src, encoding='utf-8')

# Make the original updater safe if it is ever run again.
p = Path('.github/add_screenshot_affirmations.py')
src = p.read_text(encoding='utf-8')
old = "if rows:\n    insertion = '\\n'.join(rows) + '\\n'\n    src = src[:end] + insertion + src[end:]"
new = "if rows:\n    # Ensure the existing last array row is comma-terminated before appending.\n    prefix = src[:end]\n    stripped = prefix.rstrip()\n    if stripped.endswith(']') and not stripped.endswith('],'):\n        prefix = stripped + ',' + prefix[len(stripped):]\n    insertion = '\\n'.join(rows) + '\\n'\n    src = prefix + insertion + src[end:]"
if old not in src:
    raise SystemExit('Updater insertion block not found')
src = src.replace(old, new, 1)
p.write_text(src, encoding='utf-8')

print('Fixed BASE_AFFIRMATIONS boundary and hardened screenshot updater')