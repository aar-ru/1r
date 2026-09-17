from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

s = s.replace(
"    const DAILY_GOAL_MODE = 'viewed-full-round-v2';\n",
"    const DAILY_GOAL_MODE = 'viewed-full-round-v2';\n    const ACHIEVEMENT_MODE = 'fresh-card-milestones-v2';\n"
)

s = s.replace(
"        totalCards: Math.max(0, Math.floor(Number(src.totalCards) || 0)),\n        streak:",
"        totalCards: Math.max(0, Math.floor(Number(src.totalCards) || 0)),\n        achievementCards: Math.max(0, Math.floor(Number(src.achievementCards) || 0)),\n        achievementMode: typeof src.achievementMode === 'string' ? src.achievementMode : '',\n        streak:"
)

anchor = """    function saveGameState() {\n      safeStorageSet(GAME_STATE_KEY, JSON.stringify(gameState));\n    }\n"""
insert = """    function saveGameState() {\n      safeStorageSet(GAME_STATE_KEY, JSON.stringify(gameState));\n    }\n\n    // Card milestones must count only cards genuinely viewed after this milestone system starts.\n    // Older daily-card totals were imported into totalCards when gamification was introduced,\n    // which could incorrectly pop the 100-card achievement immediately.\n    if (gameState.achievementMode !== ACHIEVEMENT_MODE) {\n      gameState.achievementMode = ACHIEVEMENT_MODE;\n      gameState.achievementCards = 0;\n      gameState.achievements = gameState.achievements.filter(id => !['cards100','cards500','cards1000'].includes(id));\n      saveGameState();\n    }\n"""
if anchor not in s:
    raise SystemExit('saveGameState anchor not found')
s = s.replace(anchor, insert, 1)

s = s.replace(
"      if (gameState.totalCards >= 100) unlockAchievement('cards100', '💯', '100 карт', 'Первая сотня прочитанных аффирмаций.');\n      if (gameState.totalCards >= 500) unlockAchievement('cards500', '🏅', '500 карт', 'Уже 500 прочитанных карт.');\n      if (gameState.totalCards >= 1000) unlockAchievement('cards1000', '🏆', '1000 карт', 'Ты прочитал 1000 карт.');\n",
"      if (gameState.achievementCards >= 100) unlockAchievement('cards100', '💯', '100 карт', 'Первая сотня прочитанных аффирмаций.');\n      if (gameState.achievementCards >= 500) unlockAchievement('cards500', '🏅', '500 карт', 'Уже 500 прочитанных карт.');\n      if (gameState.achievementCards >= 1000) unlockAchievement('cards1000', '🏆', '1000 карт', 'Ты прочитал 1000 карт.');\n"
)

s = s.replace(
"      gameState.totalCards += 1;\n      const levelChange = addXp(XP_PER_CARD);\n",
"      gameState.totalCards += 1;\n      gameState.achievementCards += 1;\n      const levelChange = addXp(XP_PER_CARD);\n",
1
)

p.write_text(s, encoding='utf-8')
print('Card achievements now count only fresh, actually viewed cards.')
