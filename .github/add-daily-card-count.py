from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

repls = [
    (
        "    const DAILY_TIME_PREFIX = 'affirm_daily_time_v1:';\n    const IDLE_TIMEOUT_MS = 30_000;",
        "    const DAILY_TIME_PREFIX = 'affirm_daily_time_v1:';\n    const DAILY_CARDS_PREFIX = 'affirm_daily_cards_v1:';\n    const IDLE_TIMEOUT_MS = 30_000;"
    ),
    (
        "    let idleTimer = null;\n    let viewedCount = 0;\n    const viewedCards = new WeakSet();\n    let lastDailyPersist = 0;",
        "    let idleTimer = null;\n    let viewedCount = Number(safeStorageGet(DAILY_CARDS_PREFIX + dayKey) || 0);\n    if (!Number.isFinite(viewedCount) || viewedCount < 0) viewedCount = 0;\n    viewedCount = Math.floor(viewedCount);\n    let viewedCards = new WeakSet();\n    let lastDailyPersist = 0;"
    ),
    (
        "    function persistDay(value = dayElapsedMs) {\n      safeStorageSet(DAILY_TIME_PREFIX + dayKey, String(Math.round(value)));\n    }\n",
        "    function persistDay(value = dayElapsedMs) {\n      safeStorageSet(DAILY_TIME_PREFIX + dayKey, String(Math.round(value)));\n    }\n\n    function persistViewedCount() {\n      safeStorageSet(DAILY_CARDS_PREFIX + dayKey, String(viewedCount));\n    }\n"
    ),
    (
        "      persistDay(dayElapsedMs);\n      dayKey = nextKey;\n      dayElapsedMs = Number(safeStorageGet(DAILY_TIME_PREFIX + dayKey) || 0);",
        "      persistDay(dayElapsedMs);\n      persistViewedCount();\n      dayKey = nextKey;\n      dayElapsedMs = Number(safeStorageGet(DAILY_TIME_PREFIX + dayKey) || 0);\n      viewedCount = Number(safeStorageGet(DAILY_CARDS_PREFIX + dayKey) || 0);\n      if (!Number.isFinite(viewedCount) || viewedCount < 0) viewedCount = 0;\n      viewedCount = Math.floor(viewedCount);\n      viewedCards = new WeakSet();"
    ),
    (
        "              viewedCards.add(entry.target);\n              viewedCount += 1;\n              updateSessionStats();",
        "              viewedCards.add(entry.target);\n              viewedCount += 1;\n              persistViewedCount();\n              updateSessionStats();"
    ),
]

for old, new in repls:
    if new in s:
        continue
    if old not in s:
        raise SystemExit('Expected block not found:\n' + old)
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('Daily card counter enabled')
