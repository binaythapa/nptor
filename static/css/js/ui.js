// ===============================
// PRACTICE STATS (MATCHED / TOTAL / ACCURACY)
// ===============================
const practiceCounter = document.getElementById('practice-count');
const practiceAccuracy = document.getElementById('practice-accuracy');
const practiceStreak = document.getElementById('practice-streak');

function getNum(key) {
  return parseInt(sessionStorage.getItem(key) || '0', 10);
}

function updatePracticeUI() {
  const total = getNum("practice_total");
  const correct = getNum("practice_correct");
  const accuracy = total > 0 ? Math.round((correct / total) * 100) : 0;

  if (practiceCounter)
    practiceCounter.textContent = `Matched: ${correct} / ${total}`;

  if (practiceAccuracy)
    practiceAccuracy.textContent = `Accuracy: ${accuracy}%`;
}

window.practiceAttempt = function ({ correct, questionId, categoryId, csrf }) {
  // update session (guest-safe)
  sessionStorage.setItem("practice_total", getNum("practice_total") + 1);
  if (correct) {
    sessionStorage.setItem("practice_correct", getNum("practice_correct") + 1);
  }

  updatePracticeUI();

  // persist if logged in
  if (questionId && csrf) {
    fetch("/quiz/practice/save/", {
      method: "POST",
      headers: {
        "X-CSRFToken": csrf,
        "Content-Type": "application/x-www-form-urlencoded"
      },
      body: `question_id=${questionId}&is_correct=${correct}`
    });
  }
};

// RESET
window.resetPracticeStats = function () {
  sessionStorage.removeItem("practice_total");
  sessionStorage.removeItem("practice_correct");
  updatePracticeUI();
};

// init
updatePracticeUI();
