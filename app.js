// ─── Telegram WebApp Init ───────────────────────────────────────────────────
const tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

// ─── State ────────────────────────────────────────────────────────────────────
let allQuestions = [];
let sessionQuestions = [];
let currentIndex = 0;
let correctCount = 0;
let hasAnswered = false;
let selectedCount = 10;

// ─── On Load ─────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
    // Setup user info from Telegram
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        const user = tg.initDataUnsafe.user;
        const fullName = user.first_name + (user.last_name ? " " + user.last_name : "");
        document.getElementById("user-name").innerText = fullName;
        const initials = encodeURIComponent(fullName);
        document.getElementById("user-photo").src =
            `https://ui-avatars.com/api/?name=${initials}&background=6c3ce1&color=fff&bold=true`;
    }

    // Load questions from static JSON
    try {
        const resp = await fetch("questions.json");
        allQuestions = await resp.json();
        document.getElementById("stat-total").innerText = allQuestions.length + " ta";
    } catch (e) {
        console.error("Savollarni yuklab bo'lmadi:", e);
        showToast("Savollarni yuklab bo'lmadi. Qayta urinib ko'ring.", "error");
    }
});

// ─── Navigation ──────────────────────────────────────────────────────────────
function navigate(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
    window.scrollTo(0, 0);

    if (viewId === 'view-dashboard') {
        tg.MainButton.hide();
        tg.BackButton.hide();
    } else {
        tg.BackButton.show();
        tg.BackButton.onClick(() => navigate('view-dashboard'));
    }
}

// ─── Category / Count Selection ──────────────────────────────────────────────
function startSetup() {
    if (allQuestions.length === 0) {
        showToast("Savollar hali yuklanmagan. Kuting...", "warn");
        return;
    }
    navigate('view-setup');

    // Build category buttons
    const cats = [...new Set(allQuestions.map(q => q.category))].filter(Boolean);
    const catContainer = document.getElementById("category-list");
    catContainer.innerHTML = '';

    // "All" button
    const allBtn = document.createElement("button");
    allBtn.className = "cat-btn active";
    allBtn.dataset.cat = "ALL";
    allBtn.innerText = "Barchasi";
    allBtn.onclick = () => selectCategory(allBtn);
    catContainer.appendChild(allBtn);

    cats.forEach(cat => {
        const btn = document.createElement("button");
        btn.className = "cat-btn";
        btn.dataset.cat = cat;
        btn.innerText = cat;
        btn.onclick = () => selectCategory(btn);
        catContainer.appendChild(btn);
    });
}

function selectCategory(btn) {
    document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
}

function selectCount(btn, count) {
    selectedCount = count;
    document.querySelectorAll('.count-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
}

function beginTest() {
    const activeCat = document.querySelector('.cat-btn.active');
    const cat = activeCat ? activeCat.dataset.cat : "ALL";

    let pool = cat === "ALL" ? allQuestions : allQuestions.filter(q => q.category === cat);

    // Shuffle
    pool = pool.sort(() => Math.random() - 0.5);
    sessionQuestions = pool.slice(0, selectedCount);

    if (sessionQuestions.length === 0) {
        showToast("Bu bo'limda savollar topilmadi!", "warn");
        return;
    }

    currentIndex = 0;
    correctCount = 0;
    navigate('view-test');
    renderQuestion();
}

// ─── Test Rendering ───────────────────────────────────────────────────────────
function renderQuestion() {
    hasAnswered = false;
    const q = sessionQuestions[currentIndex];
    const total = sessionQuestions.length;

    // Progress
    document.getElementById("question-counter").innerText = `${currentIndex + 1}/${total}`;
    const pct = ((currentIndex + 1) / total) * 100;
    document.querySelector(".progress-bar-fill").style.width = pct + "%";

    // Question text
    document.getElementById("question-text").innerText = q.text;

    // Image
    const imgContainer = document.getElementById("question-image");
    const imgEl = imgContainer.querySelector("img");
    if (q.image_url) {
        imgEl.src = q.image_url;
        imgContainer.classList.remove("hidden");
    } else {
        imgContainer.classList.add("hidden");
    }

    // Options
    const container = document.getElementById("options-container");
    container.innerHTML = '';
    q.options.forEach(opt => {
        const btn = document.createElement("button");
        btn.className = "option-btn glass-panel";
        btn.innerHTML = `<span class="option-letter">${opt.letter}</span><span class="option-text">${opt.text}</span>`;
        btn.onclick = () => selectOption(btn, opt.letter, q);
        container.appendChild(btn);
    });

    // Hide next & explanation
    document.getElementById("next-btn").classList.add("hidden");
    document.getElementById("explanation-box").classList.add("hidden");
}

function selectOption(btn, letter, q) {
    if (hasAnswered) return;
    hasAnswered = true;

    const allBtns = document.querySelectorAll('.option-btn');
    const isCorrect = letter === q.correct;

    allBtns.forEach(b => {
        const l = b.querySelector('.option-letter').innerText;
        if (l === q.correct) b.classList.add('correct');
        else if (l === letter && !isCorrect) b.classList.add('wrong');
        b.disabled = true;
    });

    if (isCorrect) {
        correctCount++;
        tg.HapticFeedback.notificationOccurred('success');
        showFloatingEmoji('✅');
    } else {
        tg.HapticFeedback.notificationOccurred('error');
        showFloatingEmoji('❌');
    }

    // Show explanation
    if (q.explanation) {
        const box = document.getElementById("explanation-box");
        box.querySelector(".explanation-text").innerText = q.explanation;
        box.classList.remove("hidden");
    }

    document.getElementById("next-btn").classList.remove("hidden");

    // Update live score
    document.getElementById("live-score").innerText = `${correctCount} / ${currentIndex + 1}`;
}

function nextQuestion() {
    currentIndex++;
    if (currentIndex >= sessionQuestions.length) {
        showResult();
    } else {
        renderQuestion();
    }
}

// ─── Results ─────────────────────────────────────────────────────────────────
function showResult() {
    navigate('view-result');
    const total = sessionQuestions.length;
    const pct = Math.round((correctCount / total) * 100);

    document.getElementById("result-score").innerText = `${correctCount} / ${total}`;
    document.getElementById("result-pct").innerText = `${pct}%`;

    const circle = document.querySelector(".result-circle-fill");
    circle.style.setProperty('--pct', pct);

    let emoji, msg;
    if (pct >= 90) { emoji = "🏆"; msg = "Mukammal natija!"; }
    else if (pct >= 70) { emoji = "🎉"; msg = "Zo'r! Davom eting!"; }
    else if (pct >= 50) { emoji = "📚"; msg = "Yaxshi, lekin o'qish kerak!"; }
    else { emoji = "💪"; msg = "Harakat qiling, uddalaysiz!"; }

    document.getElementById("result-emoji").innerText = emoji;
    document.getElementById("result-msg").innerText = msg;

    // Update dashboard stats
    const currentTests = parseInt(document.getElementById("stat-tests").innerText) || 0;
    document.getElementById("stat-tests").innerText = (currentTests + 1) + " ta";

    // Send result to bot
    tg.sendData(JSON.stringify({
        action: 'test_completed',
        correct: correctCount,
        total: total,
        pct: pct
    }));
}

function retryTest() { beginTest(); }
function goHome() { navigate('view-dashboard'); }

// ─── Helpers ─────────────────────────────────────────────────────────────────
function showToast(msg, type = "info") {
    const t = document.getElementById("toast");
    t.innerText = msg;
    t.className = `toast show ${type}`;
    setTimeout(() => t.classList.remove("show"), 3000);
}

function showFloatingEmoji(emoji) {
    const el = document.createElement("div");
    el.className = "float-emoji";
    el.innerText = emoji;
    el.style.left = (Math.random() * 60 + 20) + "%";
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 1000);
}
