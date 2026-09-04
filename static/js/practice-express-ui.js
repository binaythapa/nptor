/* ============================================================
   NPTOR — PRACTICE EXPRESS UI
   Express keeps its existing behavior but uses the same visual
   structure as the main Practice Questions page.
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
    if (window.location.pathname !== "/quiz/practice/express/") return;

    const page = document.querySelector("#main-content > .box");
    if (!page) return;

    page.classList.add("practice-express-page");

    const header = page.firstElementChild;
    if (header) {
        header.classList.remove(
            "is-flex",
            "is-align-items-center",
            "is-justify-content-space-between",
            "mb-3"
        );
        header.classList.add("practice-page-header");

        const heading = header.querySelector("h1");
        if (heading) {
            heading.className = "practice-title";
            heading.textContent = "Practice Express";
        }

        const nav = header.querySelector(".practice-mode-nav");
        if (nav) {
            const links = Array.from(nav.querySelectorAll("a"));
            const basicsLink = links.find((link) => link.href.includes("/quiz/practice/"));
            const proLink = links.find((link) => link !== basicsLink);
            let expressLink = nav.querySelector('[data-practice-express-link="1"]');

            if (!expressLink) {
                expressLink = document.createElement("a");
                expressLink.href = "/quiz/practice/express/";
                expressLink.textContent = "Express";
                expressLink.dataset.practiceExpressLink = "1";
                nav.insertBefore(expressLink, proLink || null);
            }

            [basicsLink, expressLink, proLink].filter(Boolean).forEach((link) => {
                link.className = "practice-mode";
            });
            expressLink.className = "practice-mode active";
        }
    }

    const filter = page.querySelector(".box.mb-3.p-3");
    if (filter) {
        filter.classList.add("practice-express-filter");

        const filterHeader = filter.querySelector("#filterHint")?.closest("div");
        if (filterHeader) {
            filterHeader.className = "practice-filter-header";
            filterHeader.setAttribute("role", "button");
            filterHeader.setAttribute("tabindex", "0");
            filterHeader.setAttribute("aria-expanded", "false");

            const label = filterHeader.querySelector("p");
            if (label) label.className = "practice-filter-heading";
        }

        const hint = filter.querySelector("#filterHint");
        if (hint) {
            hint.textContent = "Click to expand";
            hint.className = "practice-filter-hint";
        }

        const icon = filter.querySelector("#filterToggleIcon");
        if (icon) icon.className = "practice-filter-arrow";

        const body = filter.querySelector("#filterBody");
        if (body) {
            body.classList.add("practice-filter-body");
            body.style.maxHeight = "0px";
        }
    }

    const legacyStats = page.querySelector(".level.is-mobile");
    if (legacyStats) legacyStats.style.display = "none";

    const progress = document.createElement("section");
    progress.className = "practice-progress";
    progress.setAttribute("aria-label", "Practice progress");
    progress.innerHTML = `
        <div class="practice-progress-top">
            <span>Progress</span>
            <strong id="expressProgressCount">0 / 0</strong>
        </div>
        <div class="practice-progress-track" role="progressbar"
             aria-valuemin="0" aria-valuemax="0" aria-valuenow="0">
            <div id="expressProgressBar" class="practice-progress-bar" style="width: 0%;"></div>
        </div>
    `;

    const questionText = page.querySelector("#qText");
    const questionCard = questionText ? questionText.closest(".box") : null;
    if (questionCard) {
        page.insertBefore(progress, questionCard);
    }

    ["matched", "total", "accuracy", "pDone", "pTotal", "pBar", "timer"].forEach((id) => {
        const element = document.getElementById(id);
        if (element) element.style.display = "none";
    });

    if (questionCard) {
        questionCard.classList.add("practice-question-card");

        const meta = document.createElement("div");
        meta.className = "practice-question-meta";
        meta.innerHTML = `
            <span id="expressQuestionNumber">Question #1</span>
            <span id="expressQuestionType" class="practice-question-type">Single Answer</span>
        `;
        questionCard.insertBefore(meta, questionText);

        questionText.classList.remove("question-text");
        questionText.classList.add("practice-question-text");

        const choices = questionCard.querySelector("#choices");
        if (choices) choices.classList.add("practice-options");

        const choiceHint = questionCard.querySelector("#choiceHint");
        if (choiceHint) choiceHint.style.display = "none";

        const buttonGroup = questionCard.querySelector(".button-group");
        if (buttonGroup) {
            buttonGroup.className = "practice-card-actions";

            const submit = buttonGroup.querySelector('button[type="submit"]');
            const reset = buttonGroup.querySelector("#resetBtn");

            if (submit) {
                submit.className = "practice-btn practice-btn-primary";
                submit.textContent = "Check Answer";
                submit.style.marginLeft = "auto";
            }

            if (reset) {
                reset.className = "practice-btn practice-btn-secondary";
                reset.textContent = "Reset";
            }
        }
    }

    const syncProgress = () => {
        const done = parseInt(document.getElementById("pDone")?.textContent || "0", 10) || 0;
        const total = parseInt(document.getElementById("pTotal")?.textContent || "0", 10) || 0;
        const count = document.getElementById("expressProgressCount");
        const bar = document.getElementById("expressProgressBar");
        const track = bar?.parentElement;

        if (count) count.textContent = `${done} / ${total}`;
        if (bar) bar.style.width = total ? `${Math.min(100, (done / total) * 100)}%` : "0%";
        if (track) {
            track.setAttribute("aria-valuemax", String(total));
            track.setAttribute("aria-valuenow", String(done));
        }

        const number = document.getElementById("expressQuestionNumber");
        if (number) number.textContent = `Question #${done + 1}`;

        const type = document.getElementById("expressQuestionType");
        if (type) {
            const isMulti = !!page.querySelector('#choices input[type="checkbox"]');
            type.textContent = isMulti ? "Multiple Answer" : "Single Answer";
        }
    };

    const choices = page.querySelector("#choices");
    const progressSource = document.getElementById("pDone");
    if (choices) {
        new MutationObserver(syncProgress).observe(choices, { childList: true, subtree: true });
    }
    if (progressSource) {
        new MutationObserver(syncProgress).observe(progressSource, { childList: true, characterData: true, subtree: true });
    }
    syncProgress();

    const markChoices = () => {
        page.querySelectorAll(".choice-item").forEach((option) => {
            option.classList.add("practice-express-option");
        });
        syncProgress();
    };
    markChoices();
    if (choices) {
        new MutationObserver(markChoices).observe(choices, { childList: true, subtree: true });
    }

    if (!document.getElementById("practice-express-ui-style")) {
        const style = document.createElement("style");
        style.id = "practice-express-ui-style";
        style.textContent = `
            .practice-express-page { width: 100%; max-width: 1100px; margin: 0 auto; padding: 24px 20px 48px; box-sizing: border-box; }
            .practice-express-page .practice-page-header { display: flex; align-items: flex-end; justify-content: space-between; width: 100%; gap: 24px; margin: 0 0 22px; box-sizing: border-box; }
            .practice-express-page .practice-title { margin: 0; color: var(--text-color, #1f2937); font-size: 1.5rem; line-height: 1.3; font-weight: 400; }
            .practice-express-page .practice-mode-nav { display: flex; align-items: center; flex: 0 0 auto; gap: 0; padding: 0; border: 0; background: transparent; box-shadow: none; white-space: nowrap; }
            .practice-express-page .practice-mode { display: inline-flex; align-items: center; justify-content: center; min-height: auto; padding: 0; border-radius: 0; color: var(--muted-text-color, #6b7280); font-size: .75rem; font-weight: 500; line-height: 1.5; text-decoration: none; white-space: nowrap; background: transparent !important; box-shadow: none !important; }
            .practice-express-page .practice-mode + .practice-mode::before { content: "|"; display: inline-block; margin: 0 8px; color: var(--muted-text-color, #9ca3af); }
            .practice-express-page .practice-mode.active { color: var(--primary-color, #3273dc) !important; }
            .practice-express-page .practice-express-filter { margin: 0 0 18px !important; padding: 0 !important; border: 1px solid var(--border-color, #e5e7eb); border-radius: 12px; background: var(--surface-color, #fff); box-shadow: 0 3px 14px rgba(0,0,0,.04); overflow: hidden; }
            .practice-express-page .practice-express-filter .practice-filter-header { display: flex; align-items: center; justify-content: space-between; width: 100%; min-height: 48px; margin: 0; padding: 0 15px; box-sizing: border-box; cursor: pointer; background: transparent; color: var(--text-color, #1f2937); font: inherit; text-align: left; }
            .practice-express-page .practice-filter-heading { display: flex; align-items: center; gap: 9px; min-width: 0; margin: 0 !important; font-size: .84rem; font-weight: 800; }
            .practice-express-page .practice-filter-hint, .practice-express-page #filterHint { color: var(--muted-text-color, #9ca3af) !important; font-size: .7rem !important; font-weight: 500 !important; margin-left: 6px !important; }
            .practice-express-page .practice-filter-arrow { flex-shrink: 0; color: var(--muted-text-color, #6b7280); font-size: .75rem; }
            .practice-express-page .practice-express-filter #filterBody { width: 100%; padding: 0 15px 15px; box-sizing: border-box; overflow: hidden; }
            .practice-express-page .practice-express-filter #filterBody > .columns { margin: 0 !important; }
            .practice-express-page .practice-express-filter #filterBody .column { padding: 4px 6px 0 !important; }
            .practice-express-page .practice-express-filter #filterBody .column:first-child { padding-left: 0 !important; }
            .practice-express-page .practice-express-filter #filterBody .column:last-child { padding-right: 0 !important; }
            .practice-express-page .practice-express-filter #filterBody .field { margin: 0 !important; }
            .practice-express-page .practice-express-filter #filterBody .label { display: block; margin: 0 0 6px !important; color: var(--muted-text-color, #6b7280) !important; font-size: .72rem !important; font-weight: 700 !important; line-height: 1.35; }
            .practice-express-page .practice-express-filter #filterBody .select, .practice-express-page .practice-express-filter #filterBody select { width: 100%; box-sizing: border-box; }
            .practice-express-page .practice-express-filter #filterBody .select select { min-height: 39px; font-size: .8rem; }
            .practice-express-page .practice-progress { display: block; width: 100%; margin: 18px 0 20px; box-sizing: border-box; }
            .practice-express-page .practice-progress-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 7px; font-size: .75rem; }
            .practice-express-page .practice-progress-top span { color: var(--muted-text-color, #6b7280); }
            .practice-express-page .practice-progress-top strong { color: var(--text-color, #374151); }
            .practice-express-page .practice-progress-track { width: 100%; height: 5px; overflow: hidden; border-radius: 999px; background: var(--border-color, #e5e7eb); }
            .practice-express-page .practice-progress-bar { height: 100%; border-radius: inherit; background: var(--primary-color, #3273dc); transition: width .3s ease; }
            .practice-express-page .practice-question-card { display: block !important; width: 100%; max-width: 100%; margin: 0; padding: 22px; border: 1px solid var(--border-color, #e5e7eb); border-radius: 14px; background: var(--surface-color, #fff); box-shadow: 0 4px 18px rgba(0,0,0,.045); box-sizing: border-box; }
            .practice-express-page .practice-question-meta { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; color: var(--muted-text-color, #6b7280); font-size: .72rem; font-weight: 700; }
            .practice-express-page .practice-question-type { display: inline-flex; align-items: center; padding: 4px 8px; border-radius: 999px; background: var(--surface-hover-color, #f3f4f6); color: var(--muted-text-color, #64748b); font-size: .67rem; }
            .practice-express-page .practice-question-text { margin: 0 0 20px; color: var(--text-color, #1f2937); font-size: 1.05rem; font-weight: 400; line-height: 1.7; }
            .practice-express-page .practice-options { display: flex; flex-direction: column; gap: 7px; margin-bottom: 16px !important; }
            .practice-express-page .practice-express-option { display: flex; align-items: center; gap: 10px; min-height: 46px; padding: 7px 10px; border: 1px solid var(--border-color, #e5e7eb); border-radius: 8px; background: var(--surface-color, #fff); color: var(--text-color, #1f2937); font-size: .84rem; line-height: 1.35; box-sizing: border-box; cursor: pointer; }
            .practice-express-page .practice-express-option input { width: 15px; height: 15px; margin: 0; flex: 0 0 auto; }
            .practice-express-page .choice-marker { display: inline-flex; flex: 0 0 34px; align-items: center; justify-content: center; width: 34px; height: 34px; box-sizing: border-box; border: 2px solid #cbd5e1; border-radius: 50%; color: #334e68; background: #fff; font-size: .88rem; font-weight: 600; line-height: 1; }
            .practice-express-page .choice-content { min-width: 0; flex: 1 1 auto; }
            .practice-express-page .practice-card-actions { display: flex; align-items: center; gap: 8px; margin-top: 4px; padding-top: 14px; border-top: 1px solid var(--border-color, #e5e7eb); }
            .practice-express-page .practice-btn { display: inline-flex; align-items: center; justify-content: center; min-height: 42px; padding: 0 13px; border: 1px solid var(--border-color, #dfe3e8); border-radius: 8px; font-size: .8rem; font-weight: 700; line-height: 1; cursor: pointer; box-sizing: border-box; }
            .practice-express-page .practice-btn-primary { color: #fff; border-color: var(--primary-color, #3273dc); background: var(--primary-color, #3273dc); }
            .practice-express-page .practice-btn-secondary { color: var(--text-color, #374151); background: var(--surface-color, #fff); }
            @media (max-width: 700px) { .practice-express-page { padding: 18px 14px 32px; } .practice-express-page .practice-page-header { align-items: center; gap: 12px; } .practice-express-page .practice-title { font-size: 1.5rem; } .practice-express-page .practice-express-filter #filterBody .column { padding: 4px 0 0 !important; } }
            @media (max-width: 480px) { .practice-express-page .practice-mode { font-size: .68rem; } .practice-express-page .practice-mode + .practice-mode::before { margin: 0 5px; } .practice-express-page .practice-question-card { padding: 14px; } }
        `;
        document.head.appendChild(style);
    }
});
