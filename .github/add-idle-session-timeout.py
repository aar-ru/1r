from pathlib import Path
import re

p = Path('index.html')
src = p.read_text(encoding='utf-8')

new_block = r'''    // Session + daily active reading time. Daily total persists across reloads.
    // A session also ends after 30 seconds without interaction, even if the tab stays focused.
    const DAILY_TIME_PREFIX = 'affirm_daily_time_v1:';
    const IDLE_TIMEOUT_MS = 30_000;

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
    let sessionRunning = !document.hidden && document.hasFocus();
    let lastActivityAt = activeStartedAt;
    let idleTimer = null;
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
      return sessionRunning ? Math.max(0, now - activeStartedAt) : 0;
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
        const delta = Math.max(0, now - activeStartedAt);
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

    function stopRunningSession(endAt = performance.now()) {
      if (!sessionRunning) return;
      const delta = Math.max(0, endAt - activeStartedAt);
      sessionElapsedMs += delta;
      dayElapsedMs += delta;
      sessionRunning = false;
      persistDay(dayElapsedMs);
      updateSessionStats();
    }

    function clearIdleTimer() {
      if (idleTimer !== null) {
        clearTimeout(idleTimer);
        idleTimer = null;
      }
    }

    function endSessionOnIdle() {
      if (!sessionRunning) return;
      const now = performance.now();
      const idleFor = now - lastActivityAt;
      if (idleFor + 100 < IDLE_TIMEOUT_MS) {
        scheduleIdleCheck();
        return;
      }
      // Count up to the 30-second reading grace period, not the time left open after it.
      const endAt = Math.min(now, lastActivityAt + IDLE_TIMEOUT_MS);
      stopRunningSession(endAt);
      clearIdleTimer();
    }

    function scheduleIdleCheck() {
      clearIdleTimer();
      if (!sessionRunning) return;
      const remaining = Math.max(0, IDLE_TIMEOUT_MS - (performance.now() - lastActivityAt));
      idleTimer = setTimeout(endSessionOnIdle, remaining + 60);
    }

    function markActivity() {
      if (document.hidden || !document.hasFocus()) return;
      const now = performance.now();
      lastActivityAt = now;
      if (!sessionRunning) {
        // Activity after an idle timeout starts a genuinely new session.
        sessionElapsedMs = 0;
        activeStartedAt = now;
        sessionRunning = true;
        updateSessionStats();
      }
      scheduleIdleCheck();
    }

    function endSessionOnUnfocus() {
      rollDayIfNeeded();
      clearIdleTimer();
      stopRunningSession(performance.now());
    }

    function startNewSessionOnFocus() {
      rollDayIfNeeded();
      if (document.hidden || !document.hasFocus() || sessionRunning) return;
      const now = performance.now();
      sessionElapsedMs = 0;
      activeStartedAt = now;
      lastActivityAt = now;
      sessionRunning = true;
      updateSessionStats();
      scheduleIdleCheck();
    }

    setInterval(updateSessionStats, 250);
    if (sessionRunning) scheduleIdleCheck();

    document.addEventListener('visibilitychange', () => {
      if (document.hidden) endSessionOnUnfocus();
      else startNewSessionOnFocus();
    });

    window.addEventListener('blur', endSessionOnUnfocus);
    window.addEventListener('focus', startNewSessionOnFocus);

    // Any real interaction keeps the reading session alive.
    feed.addEventListener('scroll', markActivity, { passive: true });
    feed.addEventListener('wheel', markActivity, { passive: true });
    document.addEventListener('pointerdown', markActivity, { passive: true });
    document.addEventListener('pointermove', markActivity, { passive: true });
    document.addEventListener('touchstart', markActivity, { passive: true });
    document.addEventListener('touchmove', markActivity, { passive: true });
    document.addEventListener('keydown', markActivity);

    window.addEventListener('beforeunload', () => {
      clearIdleTimer();
      if (sessionRunning) stopRunningSession(performance.now());
      else persistDay(dayElapsedMs);
    });
'''

pattern = re.compile(r"    // Session \+ daily active reading time\. Daily total persists across reloads\..*?\n    function shuffle\(arr\) \{", re.S)
m = pattern.search(src)
if not m:
    raise SystemExit('Timer block not found')
src = src[:m.start()] + new_block + "\n    function shuffle(arr) {" + src[m.end():]
p.write_text(src, encoding='utf-8')
print('Added 30-second inactivity timeout and activity-based session restart')
