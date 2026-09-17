from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

repls = [
("""    const DAILY_GOAL_CARDS = 30;
""", """    const DAILY_GOAL_CYCLES = 1;
"""),
("""        lastGoalDate: typeof src.lastGoalDate === 'string' ? src.lastGoalDate : '',
        cycles: Math.max(0, Math.floor(Number(src.cycles) || 0)),
""", """        lastGoalDate: typeof src.lastGoalDate === 'string' ? src.lastGoalDate : '',
        lastCycleGoalDate: typeof src.lastCycleGoalDate === 'string' ? src.lastCycleGoalDate : '',
        cycles: Math.max(0, Math.floor(Number(src.cycles) || 0)),
"""),
("""      const level = gameLevel();
      const progress = Math.min(100, Math.max(0, viewedCount / DAILY_GOAL_CARDS * 100));
      document.querySelectorAll('.streak-count').forEach(el => el.textContent = visibleStreak());
      document.querySelectorAll('.xp-count').forEach(el => el.textContent = gameState.totalXp);
      document.querySelectorAll('.level-count').forEach(el => el.textContent = level);
      document.querySelectorAll('.goal-progress').forEach(el => el.textContent = `${Math.min(viewedCount, DAILY_GOAL_CARDS)} / ${DAILY_GOAL_CARDS}`);
      document.querySelectorAll('.goal-fill').forEach(el => el.style.width = `${progress}%`);
""", """      const level = gameLevel();
      const goalDone = gameState.lastCycleGoalDate === dayKey;
      const activeCard = feed.querySelector('.card.active');
      const remaining = Number(activeCard?.dataset.cycleRemaining);
      const progress = Number.isFinite(remaining) && AFFIRMATIONS.length
        ? Math.min(100, Math.max(0, (AFFIRMATIONS.length - remaining) / AFFIRMATIONS.length * 100))
        : 0;
      document.querySelectorAll('.streak-count').forEach(el => el.textContent = visibleStreak());
      document.querySelectorAll('.xp-count').forEach(el => el.textContent = gameState.totalXp);
      document.querySelectorAll('.level-count').forEach(el => el.textContent = level);
      document.querySelectorAll('.goal-progress').forEach(el => el.textContent = '1 круг');
      document.querySelectorAll('.goal-line, .goal-track').forEach(el => el.style.display = goalDone ? 'none' : '');
      document.querySelectorAll('.goal-fill').forEach(el => el.style.width = `${progress}%`);
"""),
("""    function completeDailyGoalIfNeeded(showCelebration = true) {
      if (viewedCount < DAILY_GOAL_CARDS || gameState.lastGoalDate === dayKey) return;
      const yesterday = previousDateKey(dayKey);
      gameState.streak = gameState.lastGoalDate === yesterday ? gameState.streak + 1 : 1;
      gameState.lastGoalDate = dayKey;
      saveGameState();
      const levelChange = addXp(XP_DAILY_GOAL);
      if (showCelebration) {
        showReward('🎯', 'Цель дня выполнена!', `${DAILY_GOAL_CARDS} карт · +${XP_DAILY_GOAL} XP · 🔥 ${gameState.streak} дн.`, [60,40,60]);
      }
      announceLevelUp(levelChange);
      checkAchievements();
    }
""", """    function completeDailyGoalIfNeeded(showCelebration = true) {
      if (gameState.lastCycleGoalDate === dayKey) return;
      const yesterday = previousDateKey(dayKey);
      if (gameState.lastGoalDate !== dayKey) {
        gameState.streak = gameState.lastGoalDate === yesterday ? gameState.streak + 1 : 1;
      }
      gameState.lastGoalDate = dayKey;
      gameState.lastCycleGoalDate = dayKey;
      saveGameState();
      const levelChange = addXp(XP_DAILY_GOAL);
      if (showCelebration) {
        showReward('🎯', 'Цель дня выполнена!', `1 полный круг · +${XP_DAILY_GOAL} XP · 🔥 ${gameState.streak} дн.`, [60,40,60]);
      }
      announceLevelUp(levelChange);
      checkAchievements();
      updateGameHud();
    }
"""),
("""      gameState.cycles += 1;
      saveGameState();
      const levelChange = addXp(XP_FULL_CYCLE);
""", """      gameState.cycles += 1;
      saveGameState();
      completeDailyGoalIfNeeded(true);
      const levelChange = addXp(XP_FULL_CYCLE);
"""),
("""      const levelChange = addXp(XP_PER_CARD);
      completeDailyGoalIfNeeded(true);
      completeCycle(card);
""", """      const levelChange = addXp(XP_PER_CARD);
      completeCycle(card);
"""),
("""            <span class=\"stat-line goal-line\">цель <span class=\"goal-progress\">0 / 30</span></span>
""", """            <span class=\"stat-line goal-line\">цель дня · <span class=\"goal-progress\">1 круг</span></span>
"""),
]

for old, new in repls:
    if old not in s:
        if new in s:
            continue
        raise SystemExit('Expected block not found:\n' + old[:220])
    s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('Daily goal changed to one full cycle; goal UI hides after completion')
