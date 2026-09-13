from pathlib import Path

p = Path('index.html')
src = p.read_text(encoding='utf-8')

old_next = """      const item = deck[cursor++];
      fairLastId = item.id;
      persistFairDeck();
      return item;
"""
new_next = """      const item = deck[cursor++];
      fairLastId = item.id;
      const cycleRemaining = Math.max(0, deck.length - cursor);
      persistFairDeck();
      return { ...item, cycleRemaining };
"""
if old_next not in src:
    raise SystemExit('nextItem block not found')
src = src.replace(old_next, new_next, 1)

old_stats = """            <span class=\"stat-line\">сегодня <span class=\"day-timer\">00:00</span> · <span class=\"view-count\">0</span> карт.</span>
"""
new_stats = """            <span class=\"stat-line\">сегодня <span class=\"day-timer\">00:00</span> · <span class=\"view-count\">0</span> карт.</span>
            <span class=\"stat-line\">до нового круга <span class=\"cycle-remaining\">${item.cycleRemaining}</span></span>
"""
if old_stats not in src:
    raise SystemExit('topbar stats block not found')
src = src.replace(old_stats, new_stats, 1)

p.write_text(src, encoding='utf-8')
print('Added cards-until-next-cycle counter')
