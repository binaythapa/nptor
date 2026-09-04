/* ============================================================
   NPTOR — SHARED UI
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    () => {
        function initPracticeModeNavigation() {
            const nav = document.querySelector(".practice-mode-nav");
            if (!nav || window.location.pathname !== "/quiz/practice/express/") return;

            const basicsLink = nav.querySelector('a[href*="/quiz/practice/"]');
            const proLink = nav.querySelector('a[href*="/quiz/exam"]');
            if (!basicsLink || !proLink) return;

            let expressLink = nav.querySelector('[data-practice-express-link="1"]');
            if (!expressLink) {
                expressLink = document.createElement("a");
                expressLink.href = "/quiz/practice/express/";
                expressLink.textContent = "Express";
                expressLink.className = "practice-mode active";
                expressLink.dataset.practiceExpressLink = "1";
                nav.insertBefore(expressLink, proLink);
            }

            nav.style.display = "flex";
            nav.style.alignItems = "center";
            nav.style.justifyContent = "flex-end";
            nav.style.flex = "0 0 auto";
            nav.style.width = "auto";
            nav.style.gap = "0";
            nav.style.padding = "0";
            nav.style.border = "0";
            nav.style.borderRadius = "0";
            nav.style.background = "transparent";
            nav.style.boxShadow = "none";
            nav.style.whiteSpace = "nowrap";

            nav.querySelectorAll(".practice-mode").forEach((link) => {
                link.style.display = "inline-flex";
                link.style.alignItems = "center";
                link.style.justifyContent = "center";
                link.style.minHeight = "auto";
                link.style.padding = "0";
                link.style.borderRadius = "0";
                link.style.color = "var(--muted-text-color, #6b7280)";
                link.style.fontSize = ".75rem";
                link.style.fontWeight = "500";
                link.style.lineHeight = "1.5";
                link.style.textDecoration = "none";
                link.style.whiteSpace = "nowrap";
            });

            expressLink.style.color = "var(--primary-color, #3273dc)";

            if (!document.getElementById("practice-express-nav-style")) {
                const style = document.createElement("style");
                style.id = "practice-express-nav-style";
                style.textContent = `
                    .practice-mode-nav .practice-mode + .practice-mode::before {
                        content: "|";
                        display: inline-block;
                        margin: 0 8px;
                        color: var(--muted-text-color, #9ca3af);
                    }
                    .practice-mode-nav .practice-mode:hover,
                    .practice-mode-nav .practice-mode.active {
                        background: transparent !important;
                        box-shadow: none !important;
                    }
                    .practice-mode-nav .practice-mode:hover {
                        color: var(--text-color, #1f2937);
                    }
                    .practice-mode-nav .practice-mode.active {
                        color: var(--primary-color, #3273dc) !important;
                    }
                    @media (max-width: 480px) {
                        .practice-mode-nav .practice-mode { font-size: .68rem; }
                        .practice-mode-nav .practice-mode + .practice-mode::before { margin: 0 5px; }
                    }
                `;
                document.head.appendChild(style);
            }
        }

        initPracticeModeNavigation();

        /* ====================================================
           PRACTICE FILTER NORMALIZATION
           Express uses the same filter classes and collapse
           behavior as the main Practice page. Existing Express
           select IDs are deliberately preserved because the
           Express question loader reads them directly.
           ==================================================== */
        function normalizeExpressPracticeFilter() {
            if (window.location.pathname !== "/quiz/practice/express/") return;

            const page = document.querySelector("#main-content > .box");
            const filter = page?.querySelector(".box.mb-3.p-3");
            if (!filter) return;

            const domainSelect = filter.querySelector("#domainSelect");
            const categorySelect = filter.querySelector("#categorySelect");
            const difficultySelect = filter.querySelector("#difficultySelect");
            if (!domainSelect || !categorySelect || !difficultySelect) return;

            const stylesheet = document.querySelector('link[href*="css/pages/practice.css"]');
            if (!stylesheet) {
                const link = document.createElement("link");
                link.rel = "stylesheet";
                link.href = "/static/css/pages/practice.css";
                document.head.appendChild(link);
            }

            filter.classList.remove("box", "mb-3", "p-3");
            filter.classList.add("practice-panel", "practice-filter-panel");

            const toggle = document.createElement("button");
            toggle.type = "button";
            toggle.id = "filterToggle";
            toggle.className = "practice-filter-header";
            toggle.setAttribute("aria-expanded", "false");
            toggle.setAttribute("aria-controls", "filterBody");
            toggle.innerHTML = `
                <span class="practice-filter-heading">
                    <span class="practice-filter-icon" aria-hidden="true">☰</span>
                    <span>Filters</span>
                    <small id="filterHint">Click to expand</small>
                </span>
                <span id="filterToggleIcon" class="practice-filter-arrow" aria-hidden="true">▾</span>
            `;

            const body = filter.querySelector("#filterBody");
            if (!body) return;

            const form = document.createElement("form");
            form.method = "get";
            form.className = "practice-filter-form";

            const grid = document.createElement("div");
            grid.className = "practice-filter-grid";

            const fields = [
                ["Domain", domainSelect],
                ["Category", categorySelect],
                ["Difficulty", difficultySelect],
            ];

            fields.forEach(([labelText, select]) => {
                const field = document.createElement("div");
                field.className = "practice-filter-field";

                const label = document.createElement("label");
                label.textContent = labelText;
                label.htmlFor = select.id;

                const wrap = document.createElement("div");
                wrap.className = "practice-select-wrap";
                wrap.appendChild(select);
                field.append(label, wrap);
                grid.appendChild(field);
            });

            form.appendChild(grid);
            body.className = "practice-filter-body";
            body.replaceChildren(form);
            body.style.maxHeight = "";
            body.style.padding = "";
            body.style.transition = "";
            filter.replaceChildren(toggle, body);
        }

        normalizeExpressPracticeFilter();

        /* ====================================================
           SHARED PRACTICE FILTER COLLAPSE
           ==================================================== */
        function initPracticeFilterCollapse() {
            const filterToggle = document.getElementById("filterToggle");
            const filterBody = document.getElementById("filterBody");
            const filterHint = document.getElementById("filterHint");
            const filterIcon = document.getElementById("filterToggleIcon");

            if (!filterToggle || !filterBody) return;

            const updateFilterUI = (expanded) => {
                if (!filterHint || !filterIcon) return;
                filterHint.textContent = expanded ? "(Click to collapse)" : "(Click to expand)";
                filterIcon.textContent = expanded ? "▴" : "▾";
                filterToggle.setAttribute("aria-expanded", expanded ? "true" : "false");
            };

            const setFilterState = (expanded) => {
                filterBody.classList.toggle("is-open", expanded);
                localStorage.setItem("practiceFilterExpanded", expanded ? "1" : "0");
                updateFilterUI(expanded);
            };

            filterToggle.addEventListener("click", () => {
                setFilterState(!filterBody.classList.contains("is-open"));
            });

            setFilterState(localStorage.getItem("practiceFilterExpanded") === "1");

            /* The legacy Express template still contains a DOMContentLoaded
               handler that writes max-height. Clear that legacy inline style
               after all DOMContentLoaded listeners have run so the shared
               grid-row collapse remains authoritative. */
            setTimeout(() => {
                filterBody.style.maxHeight = "";
                filterBody.style.padding = "";
                filterBody.style.transition = "";
                setFilterState(localStorage.getItem("practiceFilterExpanded") === "1");
            }, 0);
        }

        initPracticeFilterCollapse();

        const practiceCounter = document.getElementById("practice-count");
        const practiceAccuracy = document.getElementById("practice-accuracy");

        function getNum(key) {
            return parseInt(sessionStorage.getItem(key) || "0", 10);
        }

        function updatePracticeUI() {
            const total = getNum("practice_total");
            const correct = getNum("practice_correct");
            const accuracy = total > 0 ? Math.round((correct / total) * 100) : 0;
            if (practiceCounter) practiceCounter.textContent = `Matched: ${correct} / ${total}`;
            if (practiceAccuracy) practiceAccuracy.textContent = `Accuracy: ${accuracy}%`;
        }

        window.practiceAttempt = function ({ correct, questionId, csrf }) {
            sessionStorage.setItem("practice_total", getNum("practice_total") + 1);
            if (correct) sessionStorage.setItem("practice_correct", getNum("practice_correct") + 1);
            updatePracticeUI();
            if (questionId && csrf) {
                fetch("/quiz/practice/save/", {
                    method: "POST",
                    headers: { "X-CSRFToken": csrf, "Content-Type": "application/x-www-form-urlencoded" },
                    body: `question_id=${encodeURIComponent(questionId)}&is_correct=${encodeURIComponent(correct)}`
                }).catch((error) => console.error("Practice save failed:", error));
            }
        };

        window.resetPracticeStats = function () {
            sessionStorage.removeItem("practice_total");
            sessionStorage.removeItem("practice_correct");
            updatePracticeUI();
        };

        updatePracticeUI();

        document.querySelectorAll(".track-header").forEach((header) => {
            if (header.dataset.accordionInitialized === "1") return;
            header.dataset.accordionInitialized = "1";
            header.addEventListener("click", () => {
                const accordion = header.closest(".track-accordion");
                if (!accordion) return;
                accordion.classList.toggle("is-open");
                const expanded = accordion.classList.contains("is-open");
                header.setAttribute("aria-expanded", expanded ? "true" : "false");
            });
        });

        const copyBtn = document.querySelector(".email-copy");
        const toast = document.getElementById("copy-toast");
        if (copyBtn && toast) {
            copyBtn.addEventListener("click", () => {
                const email = copyBtn.dataset.email;
                if (!email) return;
                navigator.clipboard.writeText(email).then(() => {
                    toast.classList.add("show");
                    setTimeout(() => toast.classList.remove("show"), 2000);
                }).catch((error) => console.error("Unable to copy email:", error));
            });
        }
    }
);
