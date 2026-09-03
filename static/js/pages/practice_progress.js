/*
 * Practice progress synchronization.
 *
 * The question/result area is replaced after AJAX actions. Observe that
 * container instead of wrapping window.fetch so Practice has one AJAX owner.
 */
(function () {
    "use strict";

    function updateProgress() {
        const value = document.querySelector(".practice-progress-top strong");
        const bar = document.querySelector(".practice-progress-bar");
        const track = document.querySelector(".practice-progress-track");

        if (!value || !bar || !track) return;

        const match = value.textContent.trim().match(/^(\d+)\s*\/\s*(\d+)$/);
        if (!match) return;

        const done = Number(match[1]);
        const total = Number(match[2]);
        const percent = total > 0 ? Math.min(100, (done / total) * 100) : 0;

        bar.style.width = percent + "%";
        track.setAttribute("aria-valuenow", String(done));
    }

    function syncFilter() {
        const body = document.getElementById("filterBody");
        const toggle = document.getElementById("filterToggle");
        if (!body) return;

        const expanded = body.classList.contains("is-open");
        body.hidden = !expanded;
        body.style.display = expanded ? "grid" : "none";
        if (toggle) toggle.setAttribute("aria-expanded", String(expanded));
    }

    const container = document.getElementById("practiceContainer");
    let previousQuestionId = container?.querySelector("#practiceForm")?.dataset.qid || null;

    if (container && typeof MutationObserver === "function") {
        const observer = new MutationObserver(function () {
            const form = container.querySelector("#practiceForm");
            const currentQuestionId = form?.dataset.qid || null;

            /* A new question means Next/Skip completed. Answer submission
               replaces the form with a result for the same question. */
            if (
                previousQuestionId &&
                currentQuestionId &&
                previousQuestionId !== currentQuestionId
            ) {
                const value = document.querySelector(".practice-progress-top strong");
                if (value) {
                    const match = value.textContent.trim().match(/^(\d+)\s*\/\s*(\d+)$/);
                    if (match) {
                        const done = Number(match[1]);
                        const total = Number(match[2]);
                        value.textContent = Math.min(total, done + 1) + " / " + total;
                    }
                }
                updateProgress();
            }

            if (currentQuestionId) {
                previousQuestionId = currentQuestionId;
            }
        });

        observer.observe(container, { childList: true, subtree: true });
    }

    syncFilter();

    const toggle = document.getElementById("filterToggle");
    if (toggle) {
        toggle.addEventListener("click", function () {
            window.requestAnimationFrame(syncFilter);
        });
    }
})();
