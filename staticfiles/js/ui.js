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
  sessionStorage.setItem("practice_total", getNum("practice_total") + 1);
  if (correct) {
    sessionStorage.setItem("practice_correct", getNum("practice_correct") + 1);
  }

  updatePracticeUI();

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

window.resetPracticeStats = function () {
  sessionStorage.removeItem("practice_total");
  sessionStorage.removeItem("practice_correct");
  updatePracticeUI();
};

updatePracticeUI();


// ==================================================
// DOM READY (MERGED – SINGLE ENTRY POINT)
// ==================================================
document.addEventListener("DOMContentLoaded", () => {

  // ===============================
  // MOBILE SIDEBAR TOGGLE
  // ===============================
  const sidebar = document.getElementById("site-sidebar");
  const toggleBtn = document.getElementById("sidebar-toggle");

  if (sidebar && toggleBtn) {

    // Create overlay once
    let overlay = document.querySelector(".sidebar-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.className = "sidebar-overlay";
      document.body.appendChild(overlay);
    }

    function openSidebar() {
      sidebar.classList.add("is-active");
      overlay.classList.add("is-active");
      document.body.classList.add("sidebar-open");
    }

    function closeSidebar() {
      sidebar.classList.remove("is-active");
      overlay.classList.remove("is-active");
      document.body.classList.remove("sidebar-open");
    }

    toggleBtn.addEventListener("click", (e) => {
      e.preventDefault();
      openSidebar();
    });

    overlay.addEventListener("click", closeSidebar);

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeSidebar();
    });
  }

  // ===============================
  // TRACK ACCORDION TOGGLE
  // ===============================
  document.querySelectorAll(".track-header").forEach(header => {
    header.addEventListener("click", () => {
      const accordion = header.closest(".track-accordion");
      if (accordion) {
        accordion.classList.toggle("is-open");
      }
    });
  });

});
