from pathlib import Path
import json, re

sources = [
    ('confidence', Path('.github/strong_confidence.txt')),
    ('work', Path('.github/strong_work.txt')),
    ('future', Path('.github/strong_future.txt')),
    ('calm', Path('.github/strong_calm.txt')),
    ('love', Path('.github/strong_love.txt')),
]

items = []
for theme, path in sources:
    lines = [x.strip() for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
    if len(lines) != 100:
        raise SystemExit(f'{path}: expected 100 phrases, got {len(lines)}')
    items.extend((theme, text) for text in lines)

texts = [text for _, text in items]
if len(items) != 500 or len(set(texts)) != 500:
    raise SystemExit('Corpus must contain exactly 500 unique affirmations')
if max(map(len, texts)) > 110:
    bad = [(len(t), t) for t in texts if len(t) > 110]
    raise SystemExit(f'Affirmation longer than 110 characters: {bad}')
negative = re.compile(r'(^|[\s—–,.;:!?])(не|без)(?=$|[\s—–,.;:!?])', re.I)
bad_negative = [t for t in texts if negative.search(t)]
if bad_negative:
    raise SystemExit(f'Negative constructions found: {bad_negative}')

rows = [
    '      [' + json.dumps(theme, ensure_ascii=False) + ',' + json.dumps(text, ensure_ascii=False) + ']'
    for theme, text in items
]
block = '    const AFFIRMATIONS = [\n' + ',\n'.join(rows) + '\n    ].map((x, i) => ({ id: `s${i+1}`, theme: x[0], text: x[1] }));'

p = Path('index.html')
src = p.read_text(encoding='utf-8')
pattern = r"    const AFFIRMATIONS = \[.*?\n    \]\.map\(\(x, i\) => \(\{ id: `[^`]+`, theme: x\[0\], text: x\[1\] \}\)\);"
src, n = re.subn(pattern, lambda _: block, src, count=1, flags=re.S)
if n != 1:
    raise SystemExit(f'Could not replace AFFIRMATIONS block: {n}')
for old in ['affirm_curated500_saved_v2', 'affirm_strong500_saved_v1']:
    src = src.replace(old, 'affirm_strong500_saved_v2')
p.write_text(src, encoding='utf-8')
print(f'Installed {len(items)} strong affirmations; max length {max(map(len, texts))}')
