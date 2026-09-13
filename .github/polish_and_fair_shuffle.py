from pathlib import Path
import base64, json, re, zlib


def polish(text: str) -> str:
    text = text.strip()
    fixes = [
        (r'\bвыглежу\b', 'выгляжу'),
        (r'\bчто бы\b', 'чтобы'),
        (r'\bзаботиться обо мне\b', 'заботится обо мне'),
        (r'\bне злиться на меня\b', 'не злится на меня'),
        (r'\bмне понравится\b', 'мне понравиться'),
        (r'\bс счастливым концом\b', 'со счастливым концом'),
        (r'\bкомфортнее чем\b', 'комфортнее, чем'),
        (r'\bрада когда\b', 'рада, когда'),
        (r'\bвышло что\b', 'вышло, что'),
        (r'\bто что хочу\b', 'то, что хочу'),
        (r'\bсерьезно\b', 'серьёзно'),
        (r'\bее любовь\b', 'её любовь'),
        (r'\bкруги Ада\b', 'круги ада'),
        (r'\bвсе в конечном итоге\b', 'всё в конечном итоге'),
    ]
    text = text.replace('Cо ', 'Со ')
    text = text.replace('Все происходит легко и наилучшим образом происходит', 'Всё происходит легко и наилучшим образом')
    text = text.replace('Со мной все в порядке, я хорош такой, как есть', 'Со мной всё в порядке, я хорош такой, какой я есть')
    text = text.replace('Со мной все в порядке, я уже достаточный чтобы меня любили', 'Со мной всё в порядке, я уже достаточно хорош, чтобы меня любили')
    for pat, repl in fixes:
        text = re.sub(pat, repl, text, flags=re.I)
    text = re.sub(r'\s+-\s+', ' — ', text)
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)
    text = re.sub(r' {2,}', ' ', text)
    m = re.search(r'[A-Za-zА-Яа-яЁё]', text)
    if m:
        i = m.start()
        text = text[:i] + text[i].upper() + text[i+1:]
    if text and text[-1] not in '.!?…':
        text += '.'
    return text


def parse_base(src):
    pat = re.compile(r'    const BASE_AFFIRMATIONS = \[(.*?)\n    \]\.map\(\(x, i\) => \(\{ id: `u\$\{i\+1\}`, theme: x\[0\], text: x\[1\] \}\)\);', re.S)
    m = pat.search(src)
    if not m:
        raise SystemExit('BASE_AFFIRMATIONS block not found')
    raw = '[' + m.group(1) + '\n]'
    raw = re.sub(r',\s*]$', ']', raw)
    return pat, m, json.loads(raw)


def render_base(items):
    rows = ['      [' + json.dumps(t, ensure_ascii=False) + ',' + json.dumps(polish(x), ensure_ascii=False) + ']' for t, x in items]
    return '    const BASE_AFFIRMATIONS = [\n' + ',\n'.join(rows) + '\n    ].map((x, i) => ({ id: `u${i+1}`, theme: x[0], text: x[1] }));'

index = Path('index.html')
src = index.read_text(encoding='utf-8')
pat, m, items = parse_base(src)
old = [x[1] for x in items]
src = src[:m.start()] + render_base(items) + src[m.end():]

old_effective = """    const effectiveAffirmations = [
      ...editedBaseAffirmations.filter(item => !deletedAffirmationIds.has(item.id)),
      ...customAffirmations.filter(item => !deletedAffirmationIds.has(item.id))
    ];
    const AFFIRMATIONS = effectiveAffirmations.length ? effectiveAffirmations : BASE_AFFIRMATIONS.slice(0, 1);"""
new_effective = """    function affirmationTextKey(text) {
      return String(text || '').trim().toLocaleLowerCase('ru-RU').replace(/\\s+/g, ' ').replace(/[.!?…]+$/g, '');
    }

    function uniqueAffirmationsByText(items) {
      const seen = new Set();
      return items.filter(item => {
        const key = affirmationTextKey(item.text);
        if (!key || seen.has(key)) return false;
        seen.add(key);
        return true;
      });
    }

    const effectiveAffirmations = [
      ...editedBaseAffirmations.filter(item => !deletedAffirmationIds.has(item.id)),
      ...customAffirmations.filter(item => !deletedAffirmationIds.has(item.id))
    ];
    const uniqueEffectiveAffirmations = uniqueAffirmationsByText(effectiveAffirmations);
    const AFFIRMATIONS = uniqueEffectiveAffirmations.length ? uniqueEffectiveAffirmations : BASE_AFFIRMATIONS.slice(0, 1);"""
if old_effective in src:
    src = src.replace(old_effective, new_effective, 1)
elif new_effective not in src:
    raise SystemExit('effective block not found')

old_next = """    function nextItem() {
      if (cursor >= deck.length) {
        deck = shuffle(AFFIRMATIONS);
        cursor = 0;
      }
      return deck[cursor++];
    }"""
new_next = """    const FAIR_QUEUE_KEY = 'affirm_fair_queue_v1';
    let fairQueueLoaded = false;
    let fairLastId = null;

    function fairSignature() {
      return AFFIRMATIONS.map(item => item.id).join(',');
    }

    function startFreshFairDeck() {
      deck = shuffle(AFFIRMATIONS);
      cursor = 0;
      if (deck.length > 1 && fairLastId && deck[0].id === fairLastId) {
        [deck[0], deck[1]] = [deck[1], deck[0]];
      }
    }

    function loadFairDeck() {
      const signature = fairSignature();
      const byId = new Map(AFFIRMATIONS.map(item => [item.id, item]));
      let state = null;
      try { state = JSON.parse(localStorage.getItem(FAIR_QUEUE_KEY) || 'null'); } catch {}
      fairLastId = state && typeof state.lastId === 'string' ? state.lastId : null;
      if (state && state.signature === signature && Array.isArray(state.remaining)) {
        const restored = state.remaining.map(id => byId.get(id)).filter(Boolean);
        if (restored.length) {
          deck = restored;
          cursor = 0;
          fairQueueLoaded = true;
          return;
        }
      }
      startFreshFairDeck();
      fairQueueLoaded = true;
    }

    function persistFairDeck() {
      try {
        localStorage.setItem(FAIR_QUEUE_KEY, JSON.stringify({
          signature: fairSignature(),
          remaining: deck.slice(cursor).map(item => item.id),
          lastId: fairLastId
        }));
      } catch {}
    }

    function nextItem() {
      if (!fairQueueLoaded) loadFairDeck();
      if (cursor >= deck.length) startFreshFairDeck();
      const item = deck[cursor++];
      fairLastId = item.id;
      persistFairDeck();
      return item;
    }"""
if old_next in src:
    src = src.replace(old_next, new_next, 1)
elif new_next not in src:
    raise SystemExit('nextItem block not found')

index.write_text(src, encoding='utf-8')

# Canonical corpus source: same corrections, same ordering/count.
data = Path('data/user_affirmations_exact.json')
payload = data.read_text(encoding='utf-8').strip()
items2 = json.loads(zlib.decompress(base64.b64decode(payload)).decode('utf-8'))
for item in items2:
    item['text'] = polish(item['text'])
data.write_text(base64.b64encode(zlib.compress(json.dumps(items2, ensure_ascii=False).encode('utf-8'), 9)).decode('ascii'), encoding='utf-8')

# Settings should show the same deduplicated active corpus.
settings = Path('settings.html')
if settings.exists():
    s = settings.read_text(encoding='utf-8')
    old_return = """      const custom = customItems().map(x => ({...x, source:'custom'}));
      return [...editedBase.filter(x => !deleted.has(x.id)), ...custom.filter(x => !deleted.has(x.id))];"""
    new_return = """      const custom = customItems().map(x => ({...x, source:'custom'}));
      const combined = [...editedBase.filter(x => !deleted.has(x.id)), ...custom.filter(x => !deleted.has(x.id))];
      const seen = new Set();
      return combined.filter(item => {
        const key = String(item.text || '').trim().toLocaleLowerCase('ru-RU').replace(/\\s+/g, ' ').replace(/[.!?…]+$/g, '');
        if (!key || seen.has(key)) return false;
        seen.add(key);
        return true;
      });"""
    if old_return in s:
        s = s.replace(old_return, new_return, 1)
    elif new_return not in s:
        raise SystemExit('settings active list block not found')
    settings.write_text(s, encoding='utf-8')

print('Polished', sum(a != polish(a) for a in old), 'phrases; fair unique queue enabled; IDs preserved')
