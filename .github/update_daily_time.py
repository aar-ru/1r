from pathlib import Path

p = Path('index.html')
src = p.read_text(encoding='utf-8')

src = src.replace(
"""    .session-stats {
      justify-self: center;
      display: flex;
      align-items: center;
      gap: 7px;
      min-height: 34px;
      padding: 7px 11px;""",
"""    .session-stats {
      justify-self: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 1px;
      min-height: 40px;
      padding: 5px 10px;"""
)
src = src.replace(
"""      font-size: 12px;
      font-weight: 750;
      letter-spacing: .01em;
      white-space: nowrap;
      font-variant-numeric: tabular-nums;
    }
    .session-stats .dot { opacity: .45; }""",
"""      font-size: 10px;
      line-height: 1.2;
      font-weight: 750;
      letter-spacing: .01em;
      white-space: nowrap;
      font-variant-numeric: tabular-nums;
    }
    .session-stats .stat-line { display: block; }
    .session-stats .session-timer,
    .session-stats .day-timer { font-size: 12px; font-weight: 800; }"""
)

src = src.replace(
"""          <div class=\"session-stats\" aria-label=\"Статистика текущей сессии\">
            <span class=\"timer-value\">00:00</span><span class=\"dot\">•</span><span><span class=\"view-count\">0</span> карт.</span>
          </div>""",
"""          <div class=\"session-stats\" aria-label=\"Время сегодня и текущая сессия\">
            <span class=\"stat-line\">сессия <span class=\"session-timer\">00:00</span></span>
            <span class=\"stat-line\">сегодня <span class=\"day-timer\">00:00</span> · <span class=\"view-count\">0</span> карт.</span>
          </div>"""
)

old = """    // Session stats: active reading time + number of cards actually reached.
    let sessionElapsedMs = 0;
    let sessionStartedAt = performance.now();
    let sessionRunning = !document.hidden;
    let viewedCount = 0;
    const viewedCards = new WeakSet();

    function formatTime(ms) {
      const totalSeconds = Math.floor(ms / 1000);
      const minutes = Math.floor(totalSeconds / 60);
      const seconds = totalSeconds % 60;
      return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }

    function currentElapsedMs() {
      return sessionElapsedMs + (sessionRunning ? performance.now() - sessionStartedAt : 0);
    }

    function updateSessionStats() {
      const time = formatTime(currentElapsedMs());
      document.querySelectorAll('.timer-value').forEach(el => el.textContent = time);
      document.querySelectorAll('.view-count').forEach(el => el.textContent = viewedCount);
    }

    setInterval(updateSessionStats, 250);
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && sessionRunning) {
        sessionElapsedMs += performance.now() - sessionStartedAt;
        sessionRunning = false;
      } else if (!document.hidden && !sessionRunning) {
        sessionStartedAt = performance.now();
        sessionRunning = true;
      }
      updateSessionStats();
    });"""

new = """    // Session + daily active reading time. Daily total persists across reloads.
    const DAILY_TIME_PREFIX = 'affirm_daily_time_v1:';

    function localDateKey() {
      const d = new Date();
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${y}-${m}-${day}`;
    }

    let dayKey = localDateKey();
    let dayElapsedMs = Number(localStorage.getItem(DAILY_TIME_PREFIX + dayKey) || 0);
    let sessionElapsedMs = 0;
    let activeStartedAt = performance.now();
    let sessionRunning = !document.hidden;
    let viewedCount = 0;
    const viewedCards = new WeakSet();
    let lastDailyPersist = 0;

    function formatTime(ms) {
      const totalSeconds = Math.floor(ms / 1000);
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);
      const seconds = totalSeconds % 60;
      if (hours > 0) return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
      return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }

    function activeDelta(now = performance.now()) {
      return sessionRunning ? now - activeStartedAt : 0;
    }

    function currentSessionElapsedMs(now = performance.now()) {
      return sessionElapsedMs + activeDelta(now);
    }

    function currentDayElapsedMs(now = performance.now()) {
      return dayElapsedMs + activeDelta(now);
    }

    function persistDay(value = dayElapsedMs) {
      localStorage.setItem(DAILY_TIME_PREFIX + dayKey, String(Math.round(value)));
    }

    function rollDayIfNeeded() {
      const nextKey = localDateKey();
      if (nextKey === dayKey) return;
      const now = performance.now();
      if (sessionRunning) {
        const delta = now - activeStartedAt;
        sessionElapsedMs += delta;
        dayElapsedMs += delta;
        activeStartedAt = now;
      }
      persistDay(dayElapsedMs);
      dayKey = nextKey;
      dayElapsedMs = Number(localStorage.getItem(DAILY_TIME_PREFIX + dayKey) || 0);
    }

    function updateSessionStats() {
      rollDayIfNeeded();
      const now = performance.now();
      const sessionTime = formatTime(currentSessionElapsedMs(now));
      const dayTime = formatTime(currentDayElapsedMs(now));
      document.querySelectorAll('.session-timer').forEach(el => el.textContent = sessionTime);
      document.querySelectorAll('.day-timer').forEach(el => el.textContent = dayTime);
      document.querySelectorAll('.view-count').forEach(el => el.textContent = viewedCount);
      if (sessionRunning && now - lastDailyPersist > 2000) {
        persistDay(currentDayElapsedMs(now));
        lastDailyPersist = now;
      }
    }

    setInterval(updateSessionStats, 250);
    document.addEventListener('visibilitychange', () => {
      rollDayIfNeeded();
      const now = performance.now();
      if (document.hidden && sessionRunning) {
        const delta = now - activeStartedAt;
        sessionElapsedMs += delta;
        dayElapsedMs += delta;
        sessionRunning = false;
        persistDay(dayElapsedMs);
      } else if (!document.hidden && !sessionRunning) {
        activeStartedAt = now;
        sessionRunning = true;
      }
      updateSessionStats();
    });

    window.addEventListener('beforeunload', () => {
      rollDayIfNeeded();
      persistDay(currentDayElapsedMs());
    });"""

if old not in src:
    raise SystemExit('Session timing block not found')
src = src.replace(old, new)

p.write_text(src, encoding='utf-8')
print('Added daily + session timing')
