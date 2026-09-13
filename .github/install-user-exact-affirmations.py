from pathlib import Path
import base64, json, re, zlib

p = Path('index.html')
src = p.read_text(encoding='utf-8')
payload = Path('data/user_affirmations_exact.json').read_text(encoding='utf-8').strip()
items = json.loads(zlib.decompress(base64.b64decode(payload)).decode('utf-8'))

CATEGORY_SLUG = {
  'Я-концепция': 'self',
  'Решения и уверенность': 'decisions',
  'Удача и реальность': 'luck',
  'Спокойствие': 'calm',
  'Фокус и действие': 'focus',
  'Деньги и доход': 'money',
  'Богатство и образ жизни': 'lifestyle',
  'Идеи и продукты': 'ideas',
  'Ownership и партнёрство': 'ownership',
  'Команда': 'team',
  'Яна и взаимность': 'yana',
  'Любовь и отношения': 'love',
  'Семья и дом': 'family',
  'Привлекательность и близость': 'attraction',
  'Тело, здоровье и энергия': 'health',
  'Обучение и новые навыки': 'learning',
  'Новая жизнь и смысл': 'newlife',
  'Уже сбылось': 'fulfilled',
}

IMG = {
  'work': [
    'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1800&q=86',
    'https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1800&q=86',
    'https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1800&q=86'
  ],
  'future': [
    'https://images.unsplash.com/photo-1519501025264-65ba15a82390?auto=format&fit=crop&w=1800&q=86',
    'https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1800&q=86',
    'https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=1800&q=86'
  ],
  'confidence': [
    'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1800&q=86',
    'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1800&q=86',
    'https://images.unsplash.com/photo-1493246507139-91e8fad9978e?auto=format&fit=crop&w=1800&q=86'
  ],
  'calm': [
    'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1800&q=86',
    'https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=1800&q=86',
    'https://images.unsplash.com/photo-1511497584788-876760111969?auto=format&fit=crop&w=1800&q=86'
  ],
  'love': [
    'https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=1800&q=86',
    'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1800&q=86',
    'https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?auto=format&fit=crop&w=1800&q=86'
  ]
}

GROUP = {
  'Я-концепция': 'confidence', 'Решения и уверенность': 'confidence',
  'Удача и реальность': 'future', 'Спокойствие': 'calm',
  'Фокус и действие': 'work', 'Деньги и доход': 'work',
  'Богатство и образ жизни': 'future', 'Идеи и продукты': 'work',
  'Ownership и партнёрство': 'work', 'Команда': 'work',
  'Яна и взаимность': 'love', 'Любовь и отношения': 'love',
  'Семья и дом': 'love', 'Привлекательность и близость': 'love',
  'Тело, здоровье и энергия': 'calm', 'Обучение и новые навыки': 'confidence',
  'Новая жизнь и смысл': 'future', 'Уже сбылось': 'future'
}

THEMES = {
  CATEGORY_SLUG[cat]: {'label': cat, 'images': IMG[GROUP[cat]]}
  for cat in CATEGORY_SLUG
}

rows = []
for item in items:
  rows.append('      [' + json.dumps(CATEGORY_SLUG[item['category']], ensure_ascii=False) + ',' + json.dumps(item['text'], ensure_ascii=False) + ']')

themes_block = '    const THEMES = ' + json.dumps(THEMES, ensure_ascii=False, indent=2).replace('\n', '\n    ') + ';'
affirmations_block = '    const AFFIRMATIONS = [\n' + ',\n'.join(rows) + '\n    ].map((x, i) => ({ id: `u${i+1}`, theme: x[0], text: x[1] }));'

src, n1 = re.subn(
  r'    const THEMES = \{.*?\n    \};\n\n    const AFFIRMATIONS = ',
  lambda _: themes_block + '\n\n    const AFFIRMATIONS = ',
  src, count=1, flags=re.S
)
if n1 != 1:
  raise SystemExit(f'Could not replace THEMES: {n1}')

src, n2 = re.subn(
  r'    const AFFIRMATIONS = \[.*?\n    \]\.map\(\(x, i\) => \(\{ id: `[^`]+`, theme: x\[0\], text: x\[1\] \}\)\);',
  lambda _: affirmations_block,
  src, count=1, flags=re.S
)
if n2 != 1:
  raise SystemExit(f'Could not replace AFFIRMATIONS: {n2}')

for old in ['affirm_curated500_saved_v2', 'affirm_full_diary_saved_v1', 'affirm_mne_vygodno_saved', 'affirm_user_exact_v1']:
  src = src.replace(old, 'affirm_user_exact_v1')

p.write_text(src, encoding='utf-8')
print(f'Installed {len(items)} exact user affirmations across {len(THEMES)} sections')
