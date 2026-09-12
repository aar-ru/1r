from pathlib import Path
import re

files = [Path('index.html'), Path('.github/deploy_curated_500.py')]

replacements = {
    'Я вижу то, что другие упускают.': 'Я вижу скрытые возможности.',
    'Я спокойно решаю сложные задачи.': 'Я легко решаю масштабные задачи.',
    'Я умею управлять риском.': 'Я уверенно управляю капиталом.',
    'Я легко отделяю главное от лишнего.': 'Я легко выделяю самое важное.',
    'Я получаю хорошие исходы.': 'Мои ситуации складываются удачно.',
    'Моя жизнь полностью соответствует мне.': 'Моя жизнь полностью мне подходит.',
    'Я вижу сильную картину своей жизни.': 'Я ясно вижу свою прекрасную жизнь.',
    'Я чувствую себя спокойно в отношениях.': 'Мне спокойно в отношениях.',
    'Я выбираю взаимную любовь.': 'Моя любовь взаимна.',
    'Я выбираю тёплые отношения.': 'У меня тёплые отношения.',
    'Я выбираю женщину, которая выбирает меня.': 'Рядом со мной женщина, которая выбирает меня.',
    'Я выбираю отношения, где меня ценят.': 'В моих отношениях меня ценят.',
    'Я выбираю отношения, где меня хотят.': 'В моих отношениях меня хотят.',
    'Я выбираю отношения, где мне хорошо.': 'В моих отношениях мне хорошо.',
    'Я живу в взаимной любви.': 'Я живу во взаимной любви.',
    'Мы строим совместные планы.': 'У нас есть совместные планы.',
}

for p in files:
    src = p.read_text(encoding='utf-8')
    for old, new in replacements.items():
        if old not in src:
            raise SystemExit(f'Missing phrase in {p}: {old}')
        src = src.replace(old, new)
    p.write_text(src, encoding='utf-8')

src = Path('index.html').read_text(encoding='utf-8')
m = re.search(r'    const AFFIRMATIONS = \[(.*?)\n    \]\.map', src, re.S)
if not m:
    raise SystemExit('AFFIRMATIONS block not found')
texts = re.findall(r'^\s*\["[^"]+","((?:[^"\\]|\\.)*)"\],?$', m.group(1), re.M)
if len(texts) != 500:
    raise SystemExit(f'Expected 500 phrases, got {len(texts)}')
if len(set(texts)) != 500:
    raise SystemExit('Duplicates found after polish pass')
if max(map(len, texts)) > 75:
    raise SystemExit('Phrase longer than 75 chars found')
negative = re.compile(r'(^|[\s—–,.;:!?])(не|без)(?=$|[\s—–,.;:!?])', re.I)
if any(negative.search(t) for t in texts):
    raise SystemExit('Negative construction found after polish pass')
print(f'Polished {len(replacements)} phrases; corpus remains 500 unique')
