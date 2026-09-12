from pathlib import Path

p = Path('index.html')
src = p.read_text(encoding='utf-8')

src = src.replace(
    "let sessionRunning = !document.hidden;",
    "let sessionRunning = !document.hidden && document.hasFocus();"
)

old = """    setInterval(updateSessionStats, 250);
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

new = """    function endSessionOnUnfocus() {
      rollDayIfNeeded();
      if (!sessionRunning) return;
      const now = performance.now();
      const delta = now - activeStartedAt;
      sessionElapsedMs += delta;
      dayElapsedMs += delta;
      sessionRunning = false;
      persistDay(dayElapsedMs);
      updateSessionStats();
    }

    function startNewSessionOnFocus() {
      rollDayIfNeeded();
      if (document.hidden || !document.hasFocus() || sessionRunning) return;
      sessionElapsedMs = 0;
      activeStartedAt = performance.now();
      sessionRunning = true;
      updateSessionStats();
    }

    setInterval(updateSessionStats, 250);

    document.addEventListener('visibilitychange', () => {
      if (document.hidden) endSessionOnUnfocus();
      else startNewSessionOnFocus();
    });

    window.addEventListener('blur', endSessionOnUnfocus);
    window.addEventListener('focus', startNewSessionOnFocus);

    window.addEventListener('beforeunload', () => {
      if (sessionRunning) endSessionOnUnfocus();
      else persistDay(dayElapsedMs);
    });"""

if old not in src:
    raise SystemExit('Current visibility timing block not found')

src = src.replace(old, new)
p.write_text(src, encoding='utf-8')
print('Session now ends on blur/hidden and restarts on focus')
