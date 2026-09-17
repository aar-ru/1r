from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f'Anchor not found: {label}')
    if text.count(old) != 1:
        raise SystemExit(f'Anchor is not unique ({text.count(old)}): {label}')
    return text.replace(old, new, 1)


index_path = Path('index.html')
settings_path = Path('settings.html')
index = index_path.read_text(encoding='utf-8')
settings = settings_path.read_text(encoding='utf-8')

if 'affirm_game_state_v1' in index:
    print('Duolingo mechanics already present; nothing to do.')
    raise SystemExit(0)

# ---------- index.html: CSS ----------
css_anchor = """    .favorite.saved { background: rgba(255,255,255,.92); color: #111; }\n\n    .toast {"""
css_new = """    .favorite.saved { background: rgba(255,255,255,.92); color: #111; }\n\n    .game-line { color: rgba(255,255,255,.98); font-weight: 850; }\n    .goal-line { color: rgba(255,255,255,.82); }\n    .goal-track {\n      display:block;\n      width:118px;\n      height:4px;\n      margin-top:2px;\n      overflow:hidden;\n      border-radius:999px;\n      background:rgba(255,255,255,.16);\n    }\n    .goal-fill {\n      display:block;\n      width:0%;\n      height:100%;\n      border-radius:inherit;\n      background:#fff;\n      transition:width .28s ease;\n    }\n\n    .reward-overlay {\n      position:fixed;\n      inset:0;\n      z-index:80;\n      display:grid;\n      place-items:center;\n      padding:24px;\n      background:rgba(0,0,0,.68);\n      opacity:0;\n      pointer-events:none;\n      transition:opacity .2s ease;\n      backdrop-filter:blur(10px);\n      -webkit-backdrop-filter:blur(10px);\n    }\n    .reward-overlay.open { opacity:1; pointer-events:auto; }\n    .reward-card {\n      width:min(360px,100%);\n      padding:28px 22px 22px;\n      border:1px solid rgba(255,255,255,.18);\n      border-radius:30px;\n      background:linear-gradient(180deg,#222,#111);\n      box-shadow:0 30px 100px rgba(0,0,0,.58), 0 0 70px rgba(255,255,255,.08);\n      text-align:center;\n      transform:scale(.88) translateY(16px);\n      transition:transform .24s cubic-bezier(.2,.9,.2,1);\n    }\n    .reward-overlay.open .reward-card { transform:scale(1) translateY(0); }\n    .reward-emoji { font-size:58px; line-height:1; margin-bottom:14px; animation:rewardPop .55s cubic-bezier(.2,.9,.2,1); }\n    .reward-title { font-size:26px; line-height:1.06; font-weight:850; letter-spacing:-.035em; }\n    .reward-text { margin:10px auto 20px; max-width:290px; color:rgba(255,255,255,.72); font-size:14px; line-height:1.4; }\n    .reward-button { width:100%; border:0; border-radius:17px; padding:14px 16px; background:#fff; color:#111; font-weight:850; cursor:pointer; }\n    @keyframes rewardPop { 0%{transform:scale(.5) rotate(-8deg)} 70%{transform:scale(1.12) rotate(3deg)} 100%{transform:scale(1) rotate(0)} }\n\n    .toast {"""
index = replace_once(index, css_anchor, css_new, 'index CSS')

# ---------- index.html: reward overlay ----------
html_anchor = """  <div id=\"toast\" class=\"toast\">Сохранено</div>\n\n  <script>"""
html_new = """  <div id=\"toast\" class=\"toast\">Сохранено</div>\n\n  <div class=\"reward-overlay\" id=\"rewardOverlay\" role=\"dialog\" aria-modal=\"true\" aria-labelledby=\"rewardTitle\">\n    <div class=\"reward-card\">\n      <div class=\"reward-emoji\" id=\"rewardEmoji\">🏆</div>\n      <div class=\"reward-title\" id=\"rewardTitle\">Достижение</div>\n      <div class=\"reward-text\" id=\"rewardText\"></div>\n      <button class=\"reward-button\" id=\"rewardClose\" type=\"button\">Продолжить</button>\n    </div>\n  </div>\n\n  <script>"""
index = replace_once(index, html_anchor, html_new, 'reward overlay')

# ---------- index.html: game constants ----------
constants_anchor = """    const DAILY_TIME_PREFIX = 'affirm_daily_time_v1:';\n    const DAILY_CARDS_PREFIX = 'affirm_daily_cards_v1:';\n    const IDLE_TIMEOUT_MS = 30_000;"""
constants_new = """    const DAILY_TIME_PREFIX = 'affirm_daily_time_v1:';\n    const DAILY_CARDS_PREFIX = 'affirm_daily_cards_v1:';\n    const GAME_STATE_KEY = 'affirm_game_state_v1';\n    const HAPTICS_KEY = 'affirm_haptics_v1';\n    const DAILY_GOAL_CARDS = 30;\n    const XP_PER_CARD = 1;\n    const XP_DAILY_GOAL = 20;\n    const XP_FULL_CYCLE = 100;\n    const XP_PER_LEVEL = 250;\n    const IDLE_TIMEOUT_MS = 30_000;"""
index = replace_once(index, constants_anchor, constants_new, 'game constants')

# ---------- index.html: game state/functions after daily count vars ----------
state_anchor = """    let viewedCards = new WeakSet();\n    let lastDailyPersist = 0;\n\n    function formatTime(ms) {"""
state_new = r"""    let viewedCards = new WeakSet();
    let lastDailyPersist = 0;

    const rewardOverlay = document.getElementById('rewardOverlay');
    const rewardEmoji = document.getElementById('rewardEmoji');
    const rewardTitle = document.getElementById('rewardTitle');
    const rewardText = document.getElementById('rewardText');
    const rewardClose = document.getElementById('rewardClose');
    const rewardQueue = [];
    let rewardShowing = false;

    function normalizeGameState(value) {
      const src = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
      return {
        totalXp: Math.max(0, Math.floor(Number(src.totalXp) || 0)),
        totalCards: Math.max(0, Math.floor(Number(src.totalCards) || 0)),
        streak: Math.max(0, Math.floor(Number(src.streak) || 0)),
        lastGoalDate: typeof src.lastGoalDate === 'string' ? src.lastGoalDate : '',
        cycles: Math.max(0, Math.floor(Number(src.cycles) || 0)),
        achievements: Array.isArray(src.achievements) ? [...new Set(src.achievements.filter(x => typeof x === 'string'))] : []
      };
    }

    const hadGameState = safeStorageGet(GAME_STATE_KEY) !== null;
    let gameState = normalizeGameState(readStoredJson(GAME_STATE_KEY, {}));
    if (!hadGameState) {
      // Give the new system credit for cards already viewed today before this feature existed.
      gameState.totalCards = viewedCount;
      gameState.totalXp = viewedCount * XP_PER_CARD;
    }

    function saveGameState() {
      safeStorageSet(GAME_STATE_KEY, JSON.stringify(gameState));
    }

    function hapticsEnabled() {
      const value = safeStorageGet(HAPTICS_KEY);
      return value === null || (value !== '0' && value !== 'false');
    }

    function haptic(pattern) {
      if (!hapticsEnabled() || !navigator.vibrate) return;
      try { navigator.vibrate(pattern); } catch {}
    }

    function gameLevel() {
      return Math.floor(gameState.totalXp / XP_PER_LEVEL) + 1;
    }

    function previousDateKey(key) {
      const [y,m,d] = key.split('-').map(Number);
      const date = new Date(y, m - 1, d, 12, 0, 0);
      date.setDate(date.getDate() - 1);
      const yy = date.getFullYear();
      const mm = String(date.getMonth() + 1).padStart(2, '0');
      const dd = String(date.getDate()).padStart(2, '0');
      return `${yy}-${mm}-${dd}`;
    }

    function visibleStreak() {
      if (!gameState.lastGoalDate) return 0;
      if (gameState.lastGoalDate === dayKey || gameState.lastGoalDate === previousDateKey(dayKey)) return gameState.streak;
      return 0;
    }

    function updateGameHud() {
      const level = gameLevel();
      const progress = Math.min(100, Math.max(0, viewedCount / DAILY_GOAL_CARDS * 100));
      document.querySelectorAll('.streak-count').forEach(el => el.textContent = visibleStreak());
      document.querySelectorAll('.xp-count').forEach(el => el.textContent = gameState.totalXp);
      document.querySelectorAll('.level-count').forEach(el => el.textContent = level);
      document.querySelectorAll('.goal-progress').forEach(el => el.textContent = `${Math.min(viewedCount, DAILY_GOAL_CARDS)} / ${DAILY_GOAL_CARDS}`);
      document.querySelectorAll('.goal-fill').forEach(el => el.style.width = `${progress}%`);
    }

    function presentNextReward() {
      if (rewardShowing || !rewardQueue.length) return;
      const reward = rewardQueue.shift();
      rewardShowing = true;
      rewardEmoji.textContent = reward.emoji;
      rewardTitle.textContent = reward.title;
      rewardText.textContent = reward.text;
      rewardOverlay.classList.add('open');
      haptic(reward.pattern || 50);
    }

    function showReward(emoji, title, text, pattern) {
      rewardQueue.push({ emoji, title, text, pattern });
      presentNextReward();
    }

    function closeReward() {
      if (!rewardShowing) return;
      rewardOverlay.classList.remove('open');
      rewardShowing = false;
      setTimeout(presentNextReward, 180);
    }

    rewardClose.addEventListener('click', closeReward);
    rewardOverlay.addEventListener('click', (e) => { if (e.target === rewardOverlay) closeReward(); });

    function addXp(amount) {
      const oldLevel = gameLevel();
      gameState.totalXp += Math.max(0, Math.floor(amount));
      saveGameState();
      updateGameHud();
      return { oldLevel, newLevel: gameLevel() };
    }

    function announceLevelUp(change) {
      if (change.newLevel <= change.oldLevel) return;
      showReward('⭐', `Уровень ${change.newLevel}`, `У тебя уже ${gameState.totalXp} XP.`, [80,50,120]);
    }

    function unlockAchievement(id, emoji, title, text) {
      if (gameState.achievements.includes(id)) return false;
      gameState.achievements.push(id);
      saveGameState();
      showReward(emoji, title, text, [100,50,100,50,180]);
      return true;
    }

    function checkAchievements() {
      if (gameState.totalCards >= 100) unlockAchievement('cards100', '💯', '100 карт', 'Первая сотня прочитанных аффирмаций.');
      if (gameState.totalCards >= 500) unlockAchievement('cards500', '🏅', '500 карт', 'Уже 500 прочитанных карт.');
      if (gameState.totalCards >= 1000) unlockAchievement('cards1000', '🏆', '1000 карт', 'Ты прочитал 1000 карт.');
      if (gameState.streak >= 7) unlockAchievement('streak7', '🔥', '7 дней подряд', 'Неделя с выполненной дневной целью.');
      if (gameState.streak >= 30) unlockAchievement('streak30', '🔥', '30 дней подряд', 'Месяц стабильной практики.');
      if (gameState.cycles >= 1) unlockAchievement('cycle1', '🔄', 'Первый полный круг', 'Ты прошёл всю активную колоду.');
      if (gameState.cycles >= 10) unlockAchievement('cycle10', '👑', '10 полных кругов', 'Десять полных проходов по колоде.');
      if (gameLevel() >= 5) unlockAchievement('level5', '⭐', '5 уровень', 'Ты достиг 5 уровня.');
      if (gameLevel() >= 10) unlockAchievement('level10', '🌟', '10 уровень', 'Ты достиг 10 уровня.');
    }

    function completeDailyGoalIfNeeded(showCelebration = true) {
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

    function completeCycle(card) {
      if (!card || card.dataset.cycleRemaining !== '0' || card.dataset.cycleAwarded === '1') return;
      card.dataset.cycleAwarded = '1';
      gameState.cycles += 1;
      saveGameState();
      const levelChange = addXp(XP_FULL_CYCLE);
      showReward('🔄', 'Полный круг!', `Вся колода пройдена · +${XP_FULL_CYCLE} XP`, [120,60,120,60,220]);
      announceLevelUp(levelChange);
      checkAchievements();
    }

    function recordViewedCard(card) {
      viewedCount += 1;
      persistViewedCount();
      gameState.totalCards += 1;
      const levelChange = addXp(XP_PER_CARD);
      completeDailyGoalIfNeeded(true);
      completeCycle(card);
      announceLevelUp(levelChange);
      checkAchievements();
      updateSessionStats();
    }

    saveGameState();

    function formatTime(ms) {"""
index = replace_once(index, state_anchor, state_new, 'game state')

# ---------- index.html: day rollover also refreshes game HUD ----------
roll_anchor = """      viewedCount = Math.floor(viewedCount);\n      viewedCards = new WeakSet();\n    }\n\n    function updateSessionStats() {"""
roll_new = """      viewedCount = Math.floor(viewedCount);\n      viewedCards = new WeakSet();\n      updateGameHud();\n    }\n\n    function updateSessionStats() {"""
index = replace_once(index, roll_anchor, roll_new, 'roll day game refresh')

stats_anchor = """      document.querySelectorAll('.view-count').forEach(el => el.textContent = viewedCount);\n      if (sessionRunning && now - lastDailyPersist > 2000) {"""
stats_new = """      document.querySelectorAll('.view-count').forEach(el => el.textContent = viewedCount);\n      updateGameHud();\n      if (sessionRunning && now - lastDailyPersist > 2000) {"""
index = replace_once(index, stats_anchor, stats_new, 'stats game refresh')

# ---------- index.html: card markup + cycle tag ----------
dataset_anchor = """      card.className = 'card';\n      card.dataset.id = item.id;\n      const savedClass"""
dataset_new = """      card.className = 'card';\n      card.dataset.id = item.id;\n      card.dataset.cycleRemaining = String(item.cycleRemaining ?? '');\n      const savedClass"""
index = replace_once(index, dataset_anchor, dataset_new, 'cycle dataset')

hud_anchor = """            <span class=\"stat-line\">до нового круга <span class=\"cycle-remaining\">${item.cycleRemaining}</span></span>\n          </div>"""
hud_new = """            <span class=\"stat-line\">до нового круга <span class=\"cycle-remaining\">${item.cycleRemaining}</span></span>\n            <span class=\"stat-line game-line\">🔥 <span class=\"streak-count\">0</span> · ⭐ <span class=\"xp-count\">0</span> XP · ур. <span class=\"level-count\">1</span></span>\n            <span class=\"stat-line goal-line\">цель <span class=\"goal-progress\">0 / 30</span></span>\n            <span class=\"goal-track\"><span class=\"goal-fill\"></span></span>\n          </div>"""
index = replace_once(index, hud_anchor, hud_new, 'HUD markup')

# ---------- index.html: use gamified view handler ----------
view_anchor = """              viewedCards.add(entry.target);\n              viewedCount += 1;\n              persistViewedCount();\n              updateSessionStats();"""
view_new = """              viewedCards.add(entry.target);\n              recordViewedCard(entry.target);"""
index = replace_once(index, view_anchor, view_new, 'view handler')

# ---------- index.html: initial sync ----------
init_anchor = """    deck = shuffle(AFFIRMATIONS);\n    appendCards(14);\n    renderSaved();"""
init_new = """    deck = shuffle(AFFIRMATIONS);\n    appendCards(14);\n    renderSaved();\n    completeDailyGoalIfNeeded(true);\n    checkAchievements();\n    updateGameHud();"""
index = replace_once(index, init_anchor, init_new, 'initial game sync')

# ---------- settings.html: CSS ----------
settings_css_anchor = """    .loading { padding:36px 0; text-align:center; color:var(--muted); }\n  </style>"""
settings_css_new = """    .loading { padding:36px 0; text-align:center; color:var(--muted); }\n    .setting-row { display:flex; align-items:center; justify-content:space-between; gap:16px; }\n    .setting-copy { min-width:0; }\n    .setting-title { font-size:15px; font-weight:800; margin-bottom:4px; }\n    .setting-help { color:var(--muted); font-size:12px; line-height:1.4; }\n    .switch { position:relative; width:52px; height:30px; flex:0 0 52px; }\n    .switch input { position:absolute; opacity:0; pointer-events:none; }\n    .switch-track { position:absolute; inset:0; border-radius:999px; background:#2c2c2c; border:1px solid var(--line); transition:.2s ease; }\n    .switch-track::after { content:\"\"; position:absolute; top:3px; left:3px; width:22px; height:22px; border-radius:50%; background:#fff; transition:.2s ease; }\n    .switch input:checked + .switch-track { background:#fff; }\n    .switch input:checked + .switch-track::after { transform:translateX(22px); background:#111; }\n  </style>"""
settings = replace_once(settings, settings_css_anchor, settings_css_new, 'settings CSS')

# ---------- settings.html: mechanics card ----------
settings_html_anchor = """    </header>\n\n    <section class=\"card\">\n      <h2>Добавить аффирмацию</h2>"""
settings_html_new = """    </header>\n\n    <section class=\"card\">\n      <h2>Игровые механики</h2>\n      <div class=\"setting-row\">\n        <div class=\"setting-copy\">\n          <div class=\"setting-title\">Тактильные эффекты</div>\n          <div class=\"setting-help\">Вибрация на дневной цели, новом уровне, достижениях и полном круге. На iPhone браузер может не поддерживать вибрацию.</div>\n        </div>\n        <label class=\"switch\" aria-label=\"Тактильные эффекты\">\n          <input id=\"hapticsToggle\" type=\"checkbox\" />\n          <span class=\"switch-track\"></span>\n        </label>\n      </div>\n      <div class=\"setting-help\" style=\"margin-top:14px\">Дневная цель: 30 карт · +1 XP за карту · +20 XP за цель · +100 XP за полный круг.</div>\n    </section>\n\n    <section class=\"card\">\n      <h2>Добавить аффирмацию</h2>"""
settings = replace_once(settings, settings_html_anchor, settings_html_new, 'settings mechanics card')

# ---------- settings.html: key + toggle logic ----------
settings_key_anchor = """    const SAVED_KEY = 'affirm_strong500_saved_v2';\n\n    const THEME_LABELS"""
settings_key_new = """    const SAVED_KEY = 'affirm_strong500_saved_v2';\n    const HAPTICS_KEY = 'affirm_haptics_v1';\n\n    const THEME_LABELS"""
settings = replace_once(settings, settings_key_anchor, settings_key_new, 'settings haptics key')

settings_dom_anchor = """    const editTheme = document.getElementById('editTheme');\n    let base = [];"""
settings_dom_new = """    const editTheme = document.getElementById('editTheme');\n    const hapticsToggle = document.getElementById('hapticsToggle');\n    const storedHaptics = localStorage.getItem(HAPTICS_KEY);\n    hapticsToggle.checked = storedHaptics === null || (storedHaptics !== '0' && storedHaptics !== 'false');\n    hapticsToggle.addEventListener('change', () => {\n      localStorage.setItem(HAPTICS_KEY, hapticsToggle.checked ? '1' : '0');\n      if (hapticsToggle.checked && navigator.vibrate) { try { navigator.vibrate(40); } catch {} }\n    });\n    let base = [];"""
settings = replace_once(settings, settings_dom_anchor, settings_dom_new, 'settings toggle logic')

index_path.write_text(index, encoding='utf-8')
settings_path.write_text(settings, encoding='utf-8')
print('Added daily goal, XP, levels, streak, achievements, cycle reward, reward modal and haptics toggle.')
