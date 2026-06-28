// Initialize Telegram Web App
const tg = window.Telegram.WebApp;
tg.expand(); // Expand to full screen

// Setup User Info
document.addEventListener("DOMContentLoaded", () => {
    // If running inside Telegram
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        const user = tg.initDataUnsafe.user;
        document.getElementById("user-name").innerText = user.first_name + (user.last_name ? " " + user.last_name : "");
        
        // Telegram doesn't provide avatar URL directly via WebApp, 
        // so we use UI-Avatars as a fallback with their name initials
        const initials = user.first_name.charAt(0) + (user.last_name ? user.last_name.charAt(0) : "");
        document.getElementById("user-photo").src = `https://ui-avatars.com/api/?name=${initials}&background=random&color=fff`;
        
        // Tell telegram we are ready
        tg.ready();
    }
});

// Navigation Function
function navigate(viewId) {
    // Hide all views
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });
    
    // Show target view
    document.getElementById(viewId).classList.add('active');
    
    // Manage MainButton based on view
    if (viewId === 'view-dashboard') {
        tg.MainButton.hide();
    }
}

// ----------------- TEST LOGIC (Mock) -----------------
let currentQuestion = 1;
const totalQuestions = 10;
let hasAnswered = false;
let correctCount = 0;

function selectOption(btn, isCorrect) {
    if (hasAnswered) return; // Prevent multiple clicks
    hasAnswered = true;
    
    const allOptions = document.querySelectorAll('.option-btn');
    
    // Remove selection from all
    allOptions.forEach(opt => opt.classList.remove('selected', 'correct', 'wrong'));
    
    // If correct
    if (isCorrect) {
        btn.classList.add('correct');
        correctCount++;
        tg.HapticFeedback.notificationOccurred('success');
    } else {
        btn.classList.add('wrong');
        tg.HapticFeedback.notificationOccurred('error');
        // Highlight correct one (mocking option C as correct for demonstration)
        allOptions[2].classList.add('correct'); 
    }
    
    // Show Next button
    document.getElementById("next-btn").classList.remove("hidden");
}

function nextQuestion() {
    if (currentQuestion >= totalQuestions) {
        tg.showAlert(`Test yakunlandi! Siz ${totalQuestions} tadan ${correctCount} ta topdingiz.`);
        
        // Natijani botga yuborish
        tg.sendData(JSON.stringify({
            action: 'test_completed',
            correct: correctCount,
            total: totalQuestions
        }));
        
        navigate('view-dashboard');
        // Reset
        currentQuestion = 1;
        correctCount = 0;
        updateProgress();
        resetOptions();
        return;
    }
    
    currentQuestion++;
    updateProgress();
    resetOptions();
    
    // Mock new question text
    document.getElementById("question-text").innerText = `Yangi savol ${currentQuestion}: Chorrahada harakatlanish tartibi qanday?`;
}

function updateProgress() {
    document.getElementById("question-counter").innerText = `${currentQuestion}/${totalQuestions}`;
    const percent = (currentQuestion / totalQuestions) * 100;
    document.querySelector(".progress-bar-fill").style.width = `${percent}%`;
}

function resetOptions() {
    hasAnswered = false;
    document.getElementById("next-btn").classList.add("hidden");
    const allOptions = document.querySelectorAll('.option-btn');
    allOptions.forEach(opt => opt.classList.remove('selected', 'correct', 'wrong'));
}
