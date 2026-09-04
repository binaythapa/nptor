/* ============================================================
   NPTOR — SHARED UI
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        /* ====================================================
           PRACTICE MODE NAVIGATION
           Keep Practice Express visually identical to the
           shared Practice mode navigation.
           ==================================================== */

        function initPracticeModeNavigation() {
            const nav = document.querySelector(".practice-mode-nav");

            if (!nav || window.location.pathname !== "/quiz/practice/express/") {
                return;
            }

            const basicsLink = nav.querySelector('a[href*="/quiz/practice/"]');
            const proLink = nav.querySelector('a[href*="/quiz/exam"]');

            if (!basicsLink || !proLink) {
                return;
            }

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
                        .practice-mode-nav .practice-mode {
                            font-size: .68rem;
                        }
                        .practice-mode-nav .practice-mode + .practice-mode::before {
                            margin: 0 5px;
                        }
                    }
                `;
                document.head.appendChild(style);
            }
        }

        initPracticeModeNavigation();

        /* ====================================================
           EXPRESS FILTER LABEL
           Keep the same helper text as the main Practice page.
           ==================================================== */
        function initExpressFilterLabel() {
            if (window.location.pathname !== "/quiz/practice/express/") {
                return;
            }

            const filterHint = document.getElementById("filterHint");
            if (filterHint) {
                filterHint.textContent = "Click to expand";
                filterHint.hidden = false;
            }
        }

        initExpressFilterLabel();

        /* ====================================================
           EXPRESS FILTER LAYOUT
           Apply the same filter properties used by Practice Questions,
           without changing the rest of the Express page.
           ==================================================== */
        function initExpressFilterLayout() {
            if (window.location.pathname !== "/quiz/practice/express/") {
                return;
            }

            const filter = document.querySelector(".practice-express-filter");
            if (!filter) {
                return;
            }

            filter.classList.add("practice-filter-panel");

            const header = filter.querySelector(":scope > div:first-child");
            const hint = document.getElementById("filterHint");
            const heading = header?.querySelector("p");
            const body = document.getElementById("filterBody");
            const grid = body?.querySelector(":scope > .columns");

            if (header) {
                header.className = "practice-filter-header";
                header.removeAttribute("style");
            }

            if (heading) {
                heading.className = "practice-filter-heading";
                heading.classList.remove("has-text-weight-semibold", "is-size-7", "mb-0");
            }

            if (hint) {
                hint.className = "practice-filter-hint";
                hint.hidden = false;
                hint.textContent = "Click to expand";

                if (hint.tagName.toLowerCase() !== "small") {
                    const small = document.createElement("small");
                    small.id = hint.id;
                    small.className = hint.className;
                    small.textContent = hint.textContent;
                    hint.replaceWith(small);
                }
            }

            const arrow = document.getElementById("filterToggleIcon");
            if (arrow) {
                arrow.className = "practice-filter-arrow";
            }

            if (body) {
                body.classList.add("practice-filter-body");
                body.removeAttribute("style");
            }

            if (grid) {
                grid.className = "practice-filter-grid";

                grid.querySelectorAll(":scope > .column").forEach((column) => {
                    column.className = "practice-filter-field";

                    const field = column.querySelector(":scope > .field");
                    if (field) {
                        field.className = "practice-filter-field-inner";
                        field.removeAttribute("style");
                    }

                    const selectWrap = column.querySelector(".select");
                    if (selectWrap) {
                        selectWrap.classList.add("practice-select-wrap");
                    }
                });
            }
        }

        initExpressFilterLayout();

        /* ====================================================
           PRACTICE STATS
           ==================================================== */

        const practiceCounter =
            document.getElementById(
                "practice-count"
            );

        const practiceAccuracy =
            document.getElementById(
                "practice-accuracy"
            );

        function getNum(key) {
            return parseInt(
                sessionStorage.getItem(
                    key
                ) || "0",
                10
            );
        }

        function updatePracticeUI() {
            const total = getNum("practice_total");
            const correct = getNum("practice_correct");
            const accuracy =
                total > 0 ? Math.round((correct / total) * 100) : 0;

            if (practiceCounter) {
                practiceCounter.textContent = `Matched: ${correct} / ${total}`;
            }

            if (practiceAccuracy) {
                practiceAccuracy.textContent = `Accuracy: ${accuracy}%`;
            }
        }

        window.practiceAttempt =
            function ({ correct, questionId, csrf }) {
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
                        body:
                            `question_id=${encodeURIComponent(questionId)}` +
                            `&is_correct=${encodeURIComponent(correct)}`
                    }).catch((error) => {
                        console.error("Practice save failed:", error);
                    });
                }
            };

        window.resetPracticeStats = function () {
            sessionStorage.removeItem("practice_total");
            sessionStorage.removeItem("practice_correct");
            updatePracticeUI();
        };

        updatePracticeUI();

        /* ====================================================
           TRACK ACCORDION
           ==================================================== */

        document
            .querySelectorAll(".track-header")
            .forEach((header) => {
                if (header.dataset.accordionInitialized === "1") {
                    return;
                }

                header.dataset.accordionInitialized = "1";

                header.addEventListener("click", () => {
                    const accordion = header.closest(".track-accordion");
                    if (!accordion) {
                        return;
                    }

                    accordion.classList.toggle("is-open");
                    const expanded = accordion.classList.contains("is-open");
                    header.setAttribute("aria-expanded", expanded ? "true" : "false");
                });
            });

        /* ====================================================
           COPY EMAIL
           ==================================================== */

        const copyBtn = document.querySelector(".email-copy");
        const toast = document.getElementById("copy-toast");

        if (copyBtn && toast) {
            copyBtn.addEventListener("click", () => {
                const email = copyBtn.dataset.email;
                if (!email) {
                    return;
                }

                navigator.clipboard
                    .writeText(email)
                    .then(() => {
                        toast.classList.add("show");
                        setTimeout(() => {
                            toast.classList.remove("show");
                        }, 2000);
                    })
                    .catch((error) => {
                        console.error("Unable to copy email:", error);
                    });
            });
        }

    }
);