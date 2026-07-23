/* ══════════════════════════════════════════
   AVTOVATANPARVAR MINI ILOVA - app.js
   Full Featured JavaScript
══════════════════════════════════════════ */

// ── Telegram WebApp init ──
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.expand();
  tg.setHeaderColor('#0a0e1a');
  tg.setBackgroundColor('#0a0e1a');
  tg.ready();
}

// ── State ──
let allQuestions = [], allSigns = [], allRules = [], allVideos = [], allNews = [], orgInfo = null;
let testState = {
  questions: [], current: 0, correct: 0, wrong: 0,
  selectedCategory: 'Barchasi', count: 10, answered: false
};
let userStats = { tests: 0, correct: 0, wrong: 0 };
let signsFilter = 'Barchasi';

// ── Local storage stats ──
function loadStats() {
  const s = localStorage.getItem('avp_stats');
  if (s) userStats = JSON.parse(s);
  updateStatDisplay();
}
function saveStats() {
  localStorage.setItem('avp_stats', JSON.stringify(userStats));
}
function updateStatDisplay() {
  const el = id => document.getElementById(id);
  el('stat-correct').textContent = userStats.correct;
  el('stat-wrong').textContent = userStats.wrong;
  el('stat-tests').textContent = userStats.tests + ' ta';
}

// ── Data loading ──
async function loadJSON(file) {
  const r = await fetch(file);
  return await r.json();
}

async function initApp() {
  // Telegram user
  if (tg?.initDataUnsafe?.user) {
    const u = tg.initDataUnsafe.user;
    document.getElementById('user-name').textContent = u.first_name + (u.last_name ? ' ' + u.last_name : '');
    if (u.photo_url) document.getElementById('user-photo').src = u.photo_url;
  }

  loadStats();

  try {
    [allQuestions, allSigns, allRules, allVideos, allNews, orgInfo] = await Promise.all([
      loadJSON('questions.json'),
      loadJSON('signs.json'),
      loadJSON('rules.json'),
      loadJSON('videos.json'),
      loadJSON('news.json'),
      loadJSON('org_info.json').catch(() => null)
    ]);

    document.getElementById('stat-total').textContent = allQuestions.length + ' ta';
    showToast(`✅ ${allQuestions.length} ta savol yuklandi!`);
  } catch(e) {
    document.getElementById('stat-total').textContent = '0 ta';
    showToast('❌ Ma\'lumotlar yuklanmadi');
  }
}

// ── Navigation ──
function navigate(viewId) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById(viewId).classList.add('active');
  window.scrollTo(0,0);

  // Lazy load views
  if (viewId === 'view-rules') renderRules();
  if (viewId === 'view-signs') renderSigns();
  if (viewId === 'view-videos') renderVideos();
  if (viewId === 'view-news') renderNews();
  if (viewId === 'view-org') renderOrg();
  if (viewId === 'view-setup') renderCategories();
}

// ═══════════════════════════════════════
// ── TEST MODULE ──
// ═══════════════════════════════════════
function renderCategories() {
  const cats = ['Barchasi', ...new Set(allQuestions.map(q => q.category).filter(Boolean))];
  const container = document.getElementById('category-list');
  container.innerHTML = cats.map(c =>
    `<button class="cat-btn ${c === testState.selectedCategory ? 'active' : ''}"
      onclick="selectCategory(this,'${c}')">${c}</button>`
  ).join('');
}

function selectCategory(btn, cat) {
  document.querySelectorAll('#category-list .cat-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  testState.selectedCategory = cat;
}

function selectCount(btn, n) {
  document.querySelectorAll('.count-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  testState.count = n;
}

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length-1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i+1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function beginTest() {
  let pool = testState.selectedCategory === 'Barchasi'
    ? allQuestions
    : allQuestions.filter(q => q.category === testState.selectedCategory);

  if (!pool.length) { showToast('❌ Bu bo\'limda savollar yo\'q!'); return; }

  testState.questions = shuffle(pool).slice(0, testState.count);
  testState.current = 0;
  testState.correct = 0;
  testState.wrong = 0;

  navigate('view-test');
  renderQuestion();
}

function renderQuestion() {
  const q = testState.questions[testState.current];
  const total = testState.questions.length;
  const idx = testState.current;

  document.getElementById('question-counter').textContent = `${idx+1}/${total}`;
  document.getElementById('progress-bar').style.width = `${((idx+1)/total)*100}%`;
  document.getElementById('live-score').textContent = `${testState.correct}/${testState.correct + testState.wrong}`;
  document.getElementById('question-text').textContent = q.text;

  // Image
  const imgDiv = document.getElementById('question-image');
  if (q.image_url && q.image_url.startsWith('http')) {
    imgDiv.classList.remove('hidden');
    document.getElementById('question-img-el').src = q.image_url;
  } else {
    imgDiv.classList.add('hidden');
  }

  // Options
  const letters = ['A','B','C','D'];
  const opts = [q.option_a, q.option_b, q.option_c, q.option_d].filter(Boolean);
  const container = document.getElementById('options-container');
  container.innerHTML = opts.map((opt, i) => `
    <button class="option-btn" id="opt-${letters[i]}" onclick="answerQuestion('${letters[i]}')">
      <span class="opt-label">${letters[i]}</span>
      <span>${opt}</span>
    </button>
  `).join('');

  document.getElementById('explanation-box').classList.add('hidden');
  document.getElementById('next-btn').classList.add('hidden');
  testState.answered = false;
}

function answerQuestion(selected) {
  if (testState.answered) return;
  testState.answered = true;

  const q = testState.questions[testState.current];
  const isCorrect = selected === q.correct_option;

  if (isCorrect) testState.correct++;
  else testState.wrong++;

  // Visual feedback
  document.querySelectorAll('.option-btn').forEach(btn => btn.classList.add('disabled'));

  const selBtn = document.getElementById(`opt-${selected}`);
  const corrBtn = document.getElementById(`opt-${q.correct_option}`);

  if (isCorrect) {
    selBtn.classList.add('correct');
    haptic('success');
  } else {
    selBtn.classList.add('wrong');
    corrBtn.classList.add('correct');
    haptic('error');
  }

  // Explanation
  if (q.explanation) {
    document.getElementById('explanation-text').textContent = q.explanation;
    document.getElementById('explanation-box').classList.remove('hidden');
  }

  document.getElementById('live-score').textContent = `${testState.correct}/${testState.correct + testState.wrong}`;
  document.getElementById('next-btn').classList.remove('hidden');
}

function nextQuestion() {
  testState.current++;
  if (testState.current >= testState.questions.length) {
    showResult();
  } else {
    renderQuestion();
    window.scrollTo(0,0);
  }
}

function showResult() {
  userStats.tests++;
  userStats.correct += testState.correct;
  userStats.wrong += testState.wrong;
  saveStats();
  updateStatDisplay();

  const total = testState.questions.length;
  const pct = Math.round(testState.correct / total * 100);

  document.getElementById('result-pct').textContent = pct + '%';
  document.getElementById('result-correct').textContent = testState.correct + ' ta';
  document.getElementById('result-wrong').textContent = testState.wrong + ' ta';
  document.getElementById('result-total').textContent = total + ' ta';

  let emoji, msg;
  if (pct >= 90) { emoji='🏆'; msg='A\'lo! Siz haqiqiy haydovchisiz!'; }
  else if (pct >= 70) { emoji='⭐'; msg='Yaxshi! Imtihonga tayyor!'; }
  else if (pct >= 50) { emoji='📚'; msg='Qoniqarli. Ko\'proq o\'qing!'; }
  else { emoji='🔁'; msg='Qayta o\'rganish kerak!'; }

  document.getElementById('result-emoji').textContent = emoji;
  document.getElementById('result-msg').textContent = msg;

  navigate('view-result');
}

function retryTest() { beginTest(); }

function confirmQuit() {
  document.getElementById('confirm-overlay').classList.remove('hidden');
}
function closeConfirm() {
  document.getElementById('confirm-overlay').classList.add('hidden');
}
function quitTest() {
  closeConfirm();
  navigate('view-dashboard');
}

// ═══════════════════════════════════════
// ── RULES MODULE ──
// ═══════════════════════════════════════
function renderRules() {
  const container = document.getElementById('rules-container');
  if (!allRules.length) { container.innerHTML = '<p style="text-align:center;color:#64748b;padding:40px">Qoidalar yo\'q</p>'; return; }
  container.innerHTML = allRules.map((r, i) => `
    <div class="rule-item glass-panel" onclick="showRule(${r.id})">
      <div class="rule-num">${i+1}</div>
      <div class="rule-title">${r.title}</div>
      <i class="fas fa-chevron-right" style="color:#64748b;font-size:13px"></i>
    </div>
  `).join('');
}

function showRule(id) {
  const rule = allRules.find(r => r.id === id);
  if (!rule) return;
  document.getElementById('rule-detail-title').textContent = rule.title;
  document.getElementById('rule-detail-content').textContent = rule.text || 'Matn kiritilmagan.';
  navigate('view-rule-detail');
}

// ═══════════════════════════════════════
// ── SIGNS MODULE ──
// ═══════════════════════════════════════
function renderSigns() {
  const cats = ['Barchasi', ...new Set(allSigns.map(s => s.category).filter(Boolean))];
  const catList = document.getElementById('signs-category-list');
  catList.innerHTML = cats.map(c =>
    `<button class="cat-btn ${c === signsFilter ? 'active' : ''}" onclick="filterSignsCat(this,'${c}')">${c}</button>`
  ).join('');
  renderSignsGrid();
}

function filterSignsCat(btn, cat) {
  document.querySelectorAll('#signs-category-list .cat-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  signsFilter = cat;
  renderSignsGrid();
}

function filterSigns() {
  renderSignsGrid();
}

function renderSignsGrid() {
  const query = document.getElementById('signs-search')?.value?.toLowerCase() || '';
  let filtered = allSigns;
  if (signsFilter !== 'Barchasi') filtered = filtered.filter(s => s.category === signsFilter);
  if (query) filtered = filtered.filter(s => (s.name||'').toLowerCase().includes(query));

  const container = document.getElementById('signs-container');
  if (!filtered.length) { container.innerHTML = '<p style="text-align:center;color:#64748b;padding:40px">Topilmadi</p>'; return; }

  container.innerHTML = filtered.map(s => {
    const imgSrc = s.image_url || 'images/placeholder.png';
    const imgTag = `<img src="${imgSrc}" alt="${s.name}" loading="lazy" onerror="this.onerror=null; this.src='images/placeholder.png';">`;
    return `
    <div class="sign-card glass-panel" onclick="showSignDetail(${s.id})">
      ${imgTag}
      <div class="sign-name">${s.name}</div>
      <div class="sign-cat">${s.category}</div>
    </div>`;
  }).join('');
}

function showSignDetail(id) {
  const s = allSigns.find(x => x.id === id);
  if (!s) return;
  showToast(`🔍 ${s.name}`);
  // Could navigate to detail view, for now show as toast
  if (tg?.showPopup) {
    tg.showPopup({
      title: s.name,
      message: s.description || 'Tavsif kiritilmagan.',
      buttons: [{ type: 'ok' }]
    });
  } else {
    alert(`${s.name}\n\n${s.description || ''}`);
  }
}

// ═══════════════════════════════════════
// ── VIDEOS MODULE ──
// ═══════════════════════════════════════
function renderVideos() {
  const sections = ['Barchasi', ...new Set(allVideos.map(v => v.section).filter(Boolean))];
  const secList = document.getElementById('video-section-list');
  secList.innerHTML = sections.map((s,i) =>
    `<button class="cat-btn ${i===0?'active':''}" onclick="filterVideos(this,'${s}')">${s||'Umumiy'}</button>`
  ).join('');
  renderVideosList('Barchasi');
}

function filterVideos(btn, section) {
  document.querySelectorAll('#video-section-list .cat-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderVideosList(section);
}

function renderVideosList(section) {
  const container = document.getElementById('videos-container');
  let videos = section === 'Barchasi' ? allVideos : allVideos.filter(v => v.section === section);

  if (!videos.length) { container.innerHTML = '<p style="text-align:center;color:#64748b;padding:40px">Video yo\'q</p>'; return; }

  const bySec = {};
  videos.forEach(v => {
    const s = v.section || 'Umumiy';
    if (!bySec[s]) bySec[s] = [];
    bySec[s].push(v);
  });

  let html = '';
  for (const [sec, vids] of Object.entries(bySec)) {
    if (section === 'Barchasi') html += `<div class="section-header">📂 ${sec}</div>`;
    html += vids.map((v, i) => `
      <div class="video-item glass-panel" onclick="openVideo('${v.youtube_url || v.video_url || ''}', '${v.topic.replace(/'/g,"\\'")}')">
        <div class="video-icon"><i class="fas fa-play"></i></div>
        <div class="video-info">
          <div class="video-topic">${v.topic}</div>
          <div class="video-section">${v.section || 'Umumiy'} • Dars ${i+1}</div>
        </div>
        <i class="fas fa-chevron-right" style="color:#64748b;font-size:13px"></i>
      </div>
    `).join('');
  }
  container.innerHTML = html;
}

function openVideo(url, topic) {
  if (!url) { showToast('⏳ Video hali bot orqali yuklanmagan'); return; }
  if (tg?.openLink) tg.openLink(url);
  else window.open(url, '_blank');
}

// ═══════════════════════════════════════
// ── NEWS MODULE ──
// ═══════════════════════════════════════
function renderNews() {
  const container = document.getElementById('news-container');
  if (!allNews.length) { container.innerHTML = '<p style="text-align:center;color:#64748b;padding:40px">Yangiliklar yo\'q</p>'; return; }
  container.innerHTML = allNews.map(n => `
    <div class="news-card glass-panel">
      ${n.image_url ? `<img class="news-image" src="${n.image_url}" alt="${n.title}" loading="lazy">` : ''}
      <div class="news-title">${n.title}</div>
      <div class="news-content">${n.content}</div>
      ${n.button_url ? `<button class="news-btn" onclick="openLink('${n.button_url}')"><i class="fas fa-external-link-alt"></i> ${n.button_text || 'Ko\'proq'}</button>` : ''}
    </div>
  `).join('');
}

// ═══════════════════════════════════════
// ── ORG MODULE ──
// ═══════════════════════════════════════
function renderOrg() {
  const container = document.getElementById('org-container');
  const text = orgInfo?.text || 'Ma\'lumot kiritilmagan.';

  // Parse categories from text
  const prices = [
    {toifa:'A', price:'2 200 000', desc:'Mototsikl'},
    {toifa:'B', price:'6 100 000', desc:'Yengil avtomobil'},
    {toifa:'BC', price:'8 100 000', desc:'Yengil + Yuk'},
    {toifa:'C', price:'3 200 000', desc:'Yuk avtomobil'},
    {toifa:'E', price:'3 200 000', desc:'Tirkama'},
    {toifa:'D', price:'5 200 000', desc:'Avtobus'},
  ];

  const docs = [
    'Pasport yoki ID karta nusxasi',
    '083/h shakldagi tibbiy ma\'lumotnoma',
    '3x4 o\'lchamdagi 4 dona rasm'
  ];

  container.innerHTML = `
    <div class="org-content glass-panel">
      <div style="text-align:center;margin-bottom:16px">
        <div style="font-size:40px;margin-bottom:8px">🏢</div>
        <h2 style="font-size:18px;font-weight:800">AVTOVATANPARVAR</h2>
        <p style="color:#94a3b8;font-size:13px">Innovatsion avtomaktab</p>
      </div>

      <div style="margin-bottom:20px">
        <h3 style="font-size:14px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:12px">📋 O'qitiladigan toifalar</h3>
        <table class="org-table">
          <tr><th>Toifa</th><th>Turi</th><th>Narx (so'm)</th></tr>
          ${prices.map(p=>`<tr><td><strong>${p.toifa}</strong></td><td style="color:#94a3b8">${p.desc}</td><td style="color:#4ade80;font-weight:700">${p.price}</td></tr>`).join('')}
        </table>
      </div>

      <div style="margin-bottom:20px">
        <h3 style="font-size:14px;font-weight:700;color:#94a3b8;text-transform:uppercase;margin-bottom:12px">📑 Kerakli hujjatlar</h3>
        ${docs.map((d,i)=>`<div style="display:flex;gap:10px;margin-bottom:8px"><span style="color:#1a56db;font-weight:800">${i+1}.</span><span style="color:#cbd5e1">${d}</span></div>`).join('')}
      </div>

      <button class="contact-btn" onclick="openLink('https://t.me/avtovatanparvar')">
        <i class="fas fa-paper-plane"></i> Adminga murojaat
      </button>
    </div>
  `;
}

// ── Utilities ──
function openLink(url) {
  if (tg?.openLink) tg.openLink(url);
  else window.open(url, '_blank');
}

function showToast(msg, duration = 2500) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), duration);
}

function haptic(type) {
  if (tg?.HapticFeedback) {
    if (type === 'success') tg.HapticFeedback.notificationOccurred('success');
    else if (type === 'error') tg.HapticFeedback.notificationOccurred('error');
    else tg.HapticFeedback.impactOccurred('light');
  }
}

// ── Init ──
document.addEventListener('DOMContentLoaded', initApp);

// ══════════════════════════════════════════
//   ⚔️ DUEL JANG MODULI (Bot + PvP)
// ══════════════════════════════════════════

const API_BASE = 'http://localhost:3001'; // Bot bilan parallel ishlaydi

let duelMode = null; // 'bot' | 'pvp'
let duelState = {
  questions: [], current: 0,
  userScore: 0, botScore: 0,
  answered: false,
  timer: null,
  timeLeft: 15, totalTime: 15,
  // PvP
  roomId: null, userId: null, userName: null,
  oppName: 'Raqib', pollTimer: null,
};

// ── Navigation ──
function duelBack() {
  clearInterval(duelState.timer);
  clearInterval(duelState.pollTimer);
  const inGame = !document.getElementById('duel-game').classList.contains('hidden');
  if (inGame) {
    duelShowModeSelect();
  } else {
    navigate('view-dashboard');
  }
}

function duelShowModeSelect() {
  document.getElementById('duel-mode-select').classList.remove('hidden');
  document.getElementById('pvp-countdown').classList.add('hidden');
  document.getElementById('duel-game').classList.add('hidden');
  document.getElementById('duel-result').classList.add('hidden');
  document.getElementById('bot-lobby').classList.add('hidden');
  document.getElementById('pvp-lobby').classList.add('hidden');
  document.getElementById('pvp-waiting-card').classList.add('hidden');
  document.getElementById('pvp-find-btn').classList.remove('hidden');
  document.querySelectorAll('.duel-mode-card').forEach(c => c.classList.remove('selected'));
  duelMode = null;
}

function selectDuelMode(mode) {
  duelMode = mode;
  document.querySelectorAll('.duel-mode-card').forEach(c => c.classList.remove('selected'));
  document.getElementById(`mode-${mode}-card`).classList.add('selected');

  if (mode === 'bot') {
    document.getElementById('bot-lobby').classList.remove('hidden');
    document.getElementById('pvp-lobby').classList.add('hidden');
    // set user name
    const userName = tg?.initDataUnsafe?.user?.first_name || 'Siz';
    document.getElementById('duel-user-name').textContent = userName;
    document.getElementById('duel-user-score').textContent = '0';
    document.getElementById('duel-bot-score').textContent = '0';
  } else {
    document.getElementById('pvp-lobby').classList.remove('hidden');
    document.getElementById('bot-lobby').classList.add('hidden');
  }
}

function pvpTab(tab) {
  document.getElementById('pvp-find-section').classList.toggle('hidden', tab !== 'find');
  document.getElementById('pvp-code-section').classList.toggle('hidden', tab !== 'code');
  document.getElementById('pvp-tab-find').classList.toggle('active', tab === 'find');
  document.getElementById('pvp-tab-code').classList.toggle('active', tab === 'code');
}

// ══ BOT DUEL ══
function startDuel() {
  if (allQuestions.length < 10) {
    showToast('❌ Savollar yuklanmagan. Iltimos kuting.'); return;
  }
  const shuffled = [...allQuestions].sort(() => Math.random() - 0.5);
  duelState.questions = shuffled.slice(0, 10);
  duelState.current = 0;
  duelState.userScore = 0;
  duelState.botScore = 0;
  duelState.answered = false;
  document.getElementById('hud-opp-icon').textContent = '🤖';
  document.getElementById('duel-opp-label').textContent = '🤖 Avtobot';
  _duelStartGame();
}

// ══ PvP DUEL ══
function _pvpUserId() {
  return String(tg?.initDataUnsafe?.user?.id || ('guest_' + Math.random().toString(36).slice(2)));
}
function _pvpUserName() {
  return tg?.initDataUnsafe?.user?.first_name || 'O\'yinchi';
}

async function pvpFindMatch() {
  const userId = _pvpUserId();
  const userName = _pvpUserName();
  duelState.userId = userId;
  duelState.userName = userName;

  document.getElementById('pvp-find-btn').classList.add('hidden');
  document.getElementById('pvp-waiting-card').classList.remove('hidden');
  document.getElementById('pvp-room-code-display').textContent = '...';

  try {
    const res = await fetch(`${API_BASE}/duel/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, user_name: userName })
    });
    const data = await res.json();

    if (data.status === 'active') {
      // Immediately matched
      duelState.roomId = data.room_id;
      duelState.questions = data.questions;
      _pvpStartFromRoom(data);
    } else {
      // Waiting for opponent
      duelState.roomId = data.room_id;
      duelState.questions = data.questions;
      document.getElementById('pvp-room-code-display').textContent = data.room_id;
      _pvpPollForOpponent();
    }
  } catch (e) {
    showToast('❌ Server bilan aloqa yo\'q. Bot ishlayaptimi?');
    pvpCancelWait();
  }
}

function pvpShareCode() {
  const code = duelState.roomId;
  if (!code) return;
  const text = `⚔️ Meni Avtotest Duelida yengib ko'r!\nXona kodi: ${code}\nMini Ilovadan "⚔️ Duel → Do'st bilan → Kod bilan" bo'limiga kiring!`;
  if (tg?.shareUrl) {
    tg.shareUrl(text);
  } else if (navigator.share) {
    navigator.share({ text });
  } else {
    navigator.clipboard.writeText(code).then(() => showToast('✅ Kod nusxalandi!'));
  }
}

function pvpCancelWait() {
  clearInterval(duelState.pollTimer);
  duelState.roomId = null;
  document.getElementById('pvp-waiting-card').classList.add('hidden');
  document.getElementById('pvp-find-btn').classList.remove('hidden');
}

async function pvpJoinByCode() {
  const code = document.getElementById('pvp-code-input').value.trim().toUpperCase();
  if (code.length < 6) { showToast('❌ Kodni to\'liq kiriting!'); return; }

  const userId = _pvpUserId();
  const userName = _pvpUserName();
  duelState.userId = userId;
  duelState.userName = userName;

  try {
    const res = await fetch(`${API_BASE}/duel/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ room_id: code, user_id: userId, user_name: userName })
    });
    const data = await res.json();
    if (data.error) { showToast(`❌ ${data.error}`); return; }

    duelState.roomId = data.room_id || code;
    duelState.questions = data.questions;
    _pvpStartFromRoom(data);
  } catch (e) {
    showToast('❌ Server bilan aloqa yo\'q.');
  }
}

function _pvpPollForOpponent() {
  clearInterval(duelState.pollTimer);
  duelState.pollTimer = setInterval(async () => {
    if (!duelState.roomId) return;
    try {
      const res = await fetch(`${API_BASE}/duel/state/${duelState.roomId}/${duelState.userId}`);
      const data = await res.json();
      if (data.status === 'active') {
        clearInterval(duelState.pollTimer);
        const playerIds = Object.keys(data.players);
        const oppId = playerIds.find(id => id !== String(duelState.userId));
        duelState.oppName = oppId ? data.players[oppId].name : 'Raqib';
        _pvpStartFromRoom(data);
      }
    } catch (e) {}
  }, 2000);
}

function _pvpStartFromRoom(data) {
  clearInterval(duelState.pollTimer);
  document.getElementById('pvp-waiting-card').classList.add('hidden');

  // Get opponent name
  const playerIds = Object.keys(data.players || {});
  const oppId = playerIds.find(id => id !== String(duelState.userId));
  duelState.oppName = oppId ? data.players[oppId].name : 'Raqib';

  if (!duelState.questions || !duelState.questions.length) {
    showToast('❌ Savollar yuklanmadi'); return;
  }
  duelState.current = 0;
  duelState.userScore = 0;
  duelState.botScore = 0;
  duelState.answered = false;
  document.getElementById('hud-opp-icon').textContent = '🧑';
  document.getElementById('duel-opp-label').textContent = `🧑 ${duelState.oppName}`;

  // Show countdown
  _pvpShowCountdown(() => _duelStartGame());
}

function _pvpShowCountdown(callback) {
  document.getElementById('duel-mode-select').classList.add('hidden');
  document.getElementById('pvp-countdown').classList.remove('hidden');
  document.getElementById('pvp-your-name').textContent = duelState.userName || 'Siz';
  document.getElementById('pvp-opp-name').textContent = duelState.oppName;

  let n = 3;
  const el = document.getElementById('pvp-countdown-num');
  el.textContent = n;
  const t = setInterval(() => {
    n--;
    if (n <= 0) {
      clearInterval(t);
      document.getElementById('pvp-countdown').classList.add('hidden');
      callback();
    } else {
      el.textContent = n;
      haptic('light');
    }
  }, 1000);
}

// ══ SHARED GAME ENGINE ══
function _duelStartGame() {
  document.getElementById('duel-mode-select').classList.add('hidden');
  document.getElementById('duel-game').classList.remove('hidden');
  document.getElementById('duel-result').classList.add('hidden');
  updateDuelHUD();
  duelShowQuestion();
}

function updateDuelHUD() {
  document.getElementById('hud-you-score').textContent = duelState.userScore;
  document.getElementById('hud-bot-score').textContent = duelState.botScore;
  document.getElementById('duel-user-score') && (document.getElementById('duel-user-score').textContent = duelState.userScore);
  document.getElementById('duel-bot-score') && (document.getElementById('duel-bot-score').textContent = duelState.botScore);
  const qnum = duelState.current + 1;
  document.getElementById('duel-qnum').textContent = `Savol ${qnum} / ${duelState.questions.length}`;
}

function duelShowQuestion() {
  if (duelState.current >= duelState.questions.length) { duelFinish(); return; }

  const q = duelState.questions[duelState.current];
  duelState.answered = false;
  document.getElementById('duel-question-text').textContent = q.text;

  const imgBox = document.getElementById('duel-question-image');
  const imgEl = document.getElementById('duel-question-img-el');
  if (q.image_url) {
    imgEl.src = q.image_url; imgBox.classList.remove('hidden');
    imgEl.onerror = () => imgBox.classList.add('hidden');
  } else { imgBox.classList.add('hidden'); }

  const opts = [
    { label:'A', text:q.option_a, key:'A' },
    { label:'B', text:q.option_b, key:'B' },
    { label:'C', text:q.option_c, key:'C' },
    { label:'D', text:q.option_d, key:'D' },
  ].filter(o => o.text);

  const container = document.getElementById('duel-options');
  container.innerHTML = '';
  opts.forEach(opt => {
    const btn = document.createElement('button');
    btn.className = 'option-btn';
    btn.id = `duel-opt-${opt.key}`;
    btn.innerHTML = `<span class="opt-label">${opt.label}</span>${opt.text}`;
    btn.onclick = () => duelAnswer(opt.key, q.correct_option);
    container.appendChild(btn);
  });

  duelStartTimer(q.correct_option);

  // Bot AI (only in bot mode)
  if (duelMode === 'bot') {
    const botDelay = 3000 + Math.random() * 9000;
    const botCorrect = Math.random() < 0.55;
    setTimeout(() => {
      if (!duelState.answered) {
        if (botCorrect) { duelState.botScore++; updateDuelHUD(); showToast('🤖 Avtobot to\'g\'ri topdi!'); }
      }
    }, botDelay);
  }

  // PvP: poll opponent score every 3s
  if (duelMode === 'pvp' && duelState.roomId) {
    clearInterval(duelState.pollTimer);
    duelState.pollTimer = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/duel/state/${duelState.roomId}/${duelState.userId}`);
        const data = await res.json();
        const playerIds = Object.keys(data.players || {});
        const oppId = playerIds.find(id => id !== String(duelState.userId));
        if (oppId) {
          const oppScore = data.players[oppId].score;
          if (oppScore !== duelState.botScore) {
            duelState.botScore = oppScore;
            updateDuelHUD();
          }
        }
        if (data.status === 'finished' && duelState.current >= duelState.questions.length) {
          clearInterval(duelState.pollTimer);
          duelFinish();
        }
      } catch(e) {}
    }, 3000);
  }
}

function duelStartTimer(correctOption) {
  clearInterval(duelState.timer);
  duelState.timeLeft = duelState.totalTime;
  const timerEl = document.getElementById('duel-timer');
  const barEl = document.getElementById('duel-timer-bar');
  barEl.style.width = '100%';
  barEl.style.background = 'linear-gradient(90deg,#22c55e,#16a34a)';
  timerEl.classList.remove('danger');

  duelState.timer = setInterval(() => {
    duelState.timeLeft--;
    timerEl.textContent = duelState.timeLeft;
    barEl.style.width = (duelState.timeLeft / duelState.totalTime * 100) + '%';
    if (duelState.timeLeft <= 5) {
      timerEl.classList.add('danger');
      barEl.style.background = 'linear-gradient(90deg,#dc2626,#ef4444)';
      haptic('light');
    }
    if (duelState.timeLeft <= 0) {
      clearInterval(duelState.timer);
      if (!duelState.answered) duelRevealAnswer(null, correctOption);
    }
  }, 1000);
}

function duelAnswer(selected, correct) {
  if (duelState.answered) return;
  clearInterval(duelState.timer);
  duelState.answered = true;

  // PvP: submit to server
  if (duelMode === 'pvp' && duelState.roomId) {
    fetch(`${API_BASE}/duel/answer`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        room_id: duelState.roomId,
        user_id: duelState.userId,
        q_idx: duelState.current,
        answer: selected
      })
    }).catch(() => {});
  }

  duelRevealAnswer(selected, correct);
}

function duelRevealAnswer(selected, correct) {
  ['A','B','C','D'].forEach(k => {
    const btn = document.getElementById(`duel-opt-${k}`);
    if (!btn) return;
    btn.classList.add('disabled');
    if (k === correct) btn.classList.add('correct');
    else if (k === selected && selected !== correct) btn.classList.add('wrong');
  });

  if (selected === correct) {
    duelState.userScore++; haptic('success'); showToast('✅ To\'g\'ri!');
  } else if (selected) {
    haptic('error'); showToast('❌ Xato!');
  } else {
    showToast('⏱ Vaqt tugadi!');
  }

  updateDuelHUD();
  setTimeout(() => { duelState.current++; updateDuelHUD(); duelShowQuestion(); }, 1500);
}

function duelFinish() {
  clearInterval(duelState.timer);
  clearInterval(duelState.pollTimer);
  document.getElementById('duel-game').classList.add('hidden');
  document.getElementById('duel-result').classList.remove('hidden');

  const you = duelState.userScore;
  const bot = duelState.botScore;
  const total = duelState.questions.length;
  const banner = document.getElementById('duel-result-banner');
  const emoji = document.getElementById('duel-result-emoji');
  const title = document.getElementById('duel-result-title');
  const sub = document.getElementById('duel-result-sub');

  banner.classList.remove('win','lose','draw');
  if (you > bot) {
    banner.classList.add('win'); emoji.textContent = '🏆'; title.textContent = 'G\'ALABA!';
    sub.textContent = `${duelMode === 'pvp' ? duelState.oppName : 'Avtobot'} ustidan ${you}-${bot} hisobida g'olib bo'ldingiz!`;
    haptic('success');
    if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
  } else if (you < bot) {
    banner.classList.add('lose'); emoji.textContent = '😤'; title.textContent = 'MAG\'LUBIYAT';
    sub.textContent = `Raqib ${bot}-${you} hisobida yutdi. Qayta urining!`;
    haptic('error');
  } else {
    banner.classList.add('draw'); emoji.textContent = '🤝'; title.textContent = 'DURRANG!';
    sub.textContent = `${you}-${bot} — teng natija. Rematch?`;
  }
  document.getElementById('duel-final-you').textContent = `${you} / ${total}`;
  document.getElementById('duel-final-bot').textContent = `${bot} / ${total}`;
}

function duelPlayAgain() {
  if (duelMode === 'bot') startDuel();
  else duelShowModeSelect();
}


}

