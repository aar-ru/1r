from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

# Add a dedicated per-day progress counter. The fair queue is consumed on render/preload,
# so it must never be used to decide whether the daily goal was actually completed.
s = s.replace(
"    const HAPTICS_KEY = 'affirm_haptics_v1';\n",
"    const HAPTICS_KEY = 'affirm_haptics_v1';\n    const DAILY_GOAL_PROGRESS_PREFIX = 'affirm_daily_round_progress_v2:';\n    const DAILY_GOAL_MODE = 'viewed-full-round-v2';\n"
)

s = s.replace(
"        lastCycleGoalDate: typeof src.lastCycleGoalDate === 'string' ? src.lastCycleGoalDate : '',\n        cycles:",
"        lastCycleGoalDate: typeof src.lastCycleGoalDate === 'string' ? src.lastCycleGoalDate : '',\n        goalMode: typeof src.goalMode === 'string' ? src.goalMode : '',\n        cycles:"
)

old = """    const hadGameState = safeStorageGet(GAME_STATE_KEY) !== null;\n    let gameState = normalizeGameState(readStoredJson(GAME_STATE_KEY, {}));\n    if (!hadGameState) {\n      // Give the new system credit for cards already viewed today before this feature existed.\n      gameState.totalCards = viewedCount;\n      gameState.totalXp = viewedCount * XP_PER_CARD;\n    }\n"""
new = """    const hadGameState = safeStorageGet(GAME_STATE_KEY) !== null;\n    let gameState = normalizeGameState(readStoredJson(GAME_STATE_KEY, {}));\n    if (!hadGameState) {\n      // Give the new system credit for cards already viewed today before this feature existed.\n      gameState.totalCards = viewedCount;\n      gameState.totalXp = viewedCount * XP_PER_CARD;\n    }\n\n    // v2: a daily round is earned only by cards actually viewed after this goal starts.\n    // Reset the false same-day completion created by the old render/preload-based cycle logic once.\n    let dailyGoalViewed = Number(safeStorageGet(DAILY_GOAL_PROGRESS_PREFIX + dayKey) || 0);\n    if (!Number.isFinite(dailyGoalViewed) || dailyGoalViewed < 0) dailyGoalViewed = 0;\n    dailyGoalViewed = Math.floor(dailyGoalViewed);\n    if (gameState.goalMode !== DAILY_GOAL_MODE) {\n      gameState.goalMode = DAILY_GOAL_MODE;\n      gameState.lastCycleGoalDate = '';\n      dailyGoalViewed = 0;\n      safeStorageSet(DAILY_GOAL_PROGRESS_PREFIX + dayKey, '0');\n    }\n\n    function persistDailyGoalProgress() {\n      safeStorageSet(DAILY_GOAL_PROGRESS_PREFIX + dayKey, String(dailyGoalViewed));\n    }\n"""
if old not in s:
    raise SystemExit('game state anchor not found')
s = s.replace(old, new)

old = """      const goalDone = gameState.lastCycleGoalDate === dayKey;\n      const activeCard = feed.querySelector('.card.active');\n      const remaining = Number(activeCard?.dataset.cycleRemaining);\n      const progress = Number.isFinite(remaining) && AFFIRMATIONS.length\n        ? Math.min(100, Math.max(0, (AFFIRMATIONS.length - remaining) / AFFIRMATIONS.length * 100))\n        : 0;\n"""
new = """      const goalDone = gameState.lastCycleGoalDate === dayKey;\n      const progress = AFFIRMATIONS.length\n        ? Math.min(100, Math.max(0, dailyGoalViewed / AFFIRMATIONS.length * 100))\n        : 0;\n"""
if old not in s:
    raise SystemExit('hud progress anchor not found')
s = s.replace(old, new)

s = s.replace(
"      document.querySelectorAll('.goal-progress').forEach(el => el.textContent = '1 круг');\n",
"      document.querySelectorAll('.goal-progress').forEach(el => el.textContent = `1 круг · ${Math.min(dailyGoalViewed, AFFIRMATIONS.length)} / ${AFFIRMATIONS.length}`);\n"
)

s = s.replace(
"    function completeDailyGoalIfNeeded(showCelebration = true) {\n      if (gameState.lastCycleGoalDate === dayKey) return;\n",
"    function completeDailyGoalIfNeeded(showCelebration = true) {\n      if (gameState.lastCycleGoalDate === dayKey || dailyGoalViewed < AFFIRMATIONS.length) return;\n"
)

# A fair-queue cycle boundary still awards its separate cycle XP, but no longer completes the daily goal.
s = s.replace(
"      saveGameState();\n      completeDailyGoalIfNeeded(true);\n      const levelChange = addXp(XP_FULL_CYCLE);\n",
"      saveGameState();\n      const levelChange = addXp(XP_FULL_CYCLE);\n"
)

old = """    function recordViewedCard(card) {\n      viewedCount += 1;\n      persistViewedCount();\n      gameState.totalCards += 1;\n      const levelChange = addXp(XP_PER_CARD);\n      completeCycle(card);\n      announceLevelUp(levelChange);\n"""
new = """    function recordViewedCard(card) {\n      viewedCount += 1;\n      persistViewedCount();\n      if (gameState.lastCycleGoalDate !== dayKey) {\n        dailyGoalViewed += 1;\n        persistDailyGoalProgress();\n      }\n      gameState.totalCards += 1;\n      const levelChange = addXp(XP_PER_CARD);\n      completeDailyGoalIfNeeded(true);\n      completeCycle(card);\n      announceLevelUp(levelChange);\n"""
if old not in s:
    raise SystemExit('record viewed anchor not found')
s = s.replace(old, new)

old = """      viewedCount = Math.floor(viewedCount);\n      viewedCards = new WeakSet();\n      updateGameHud();\n"""
new = """      viewedCount = Math.floor(viewedCount);\n      dailyGoalViewed = Number(safeStorageGet(DAILY_GOAL_PROGRESS_PREFIX + dayKey) || 0);\n      if (!Number.isFinite(dailyGoalViewed) || dailyGoalViewed < 0) dailyGoalViewed = 0;\n      dailyGoalViewed = Math.floor(dailyGoalViewed);\n      viewedCards = new WeakSet();\n      updateGameHud();\n"""
if old not in s:
    raise SystemExit('roll day anchor not found')
s = s.replace(old, new)

p.write_text(s, encoding='utf-8')
print('Daily goal now uses actual viewed-card progress and resets false old completion once.')
