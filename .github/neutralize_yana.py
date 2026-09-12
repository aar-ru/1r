from pathlib import Path

files = [Path('index.html'), Path('.github/update_full_diary.py')]
replacements = [
    ('контакт с Яной уже есть', 'контакт с ней уже есть'),
    ('между мной и Яной есть', 'между нами есть'),
    ('Наше общение с Яной становится', 'Наше общение с ней становится'),
    ('Яна хочет продолжать со мной общаться.', 'Она хочет продолжать со мной общаться.'),
    ('Наше с Яной общение становится', 'Наше общение становится'),
    ('Яна сама проявляется', 'Она сама проявляется'),
    ('Мы с Яной уже сблизились.', 'Мы уже сблизились.'),
    ('Наш с Яной контакт уже стал', 'Наш контакт уже стал'),
    ('наши отношения с Яной движутся', 'наши отношения движутся'),
    ('Яна ценит меня', 'Она ценит меня'),
]

for path in files:
    src = path.read_text(encoding='utf-8')
    for old, new in replacements:
        src = src.replace(old, new)
    if 'Яна' in src or 'Яной' in src:
        positions = [i for i in range(len(src)) if src.startswith('Яна', i) or src.startswith('Яной', i)]
        snippets = [src[max(0,i-60):i+100].replace('\n',' ') for i in positions[:10]]
        raise SystemExit(f'Unreplaced name in {path}: {snippets}')
    path.write_text(src, encoding='utf-8')
    print(f'Neutralized relationship wording in {path}')
