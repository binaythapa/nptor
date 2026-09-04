/* ============================================================
   NPTOR — PRACTICE EXPRESS UI
   Keeps Express behavior intact while using the same visual shell
   as the main Practice page.
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
    if (window.location.pathname !== "/quiz/practice/express/") {
        return;
    }

    const page = document.querySelector("#main-content > .box");
    if (!page) {
        return;
    }

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
            heading.classList.remove("title", "is-5", "mb-0", "has-text-weight-semibold");
            heading.classList.add("practice-title");

            if (!header.querySelector(".practice-eyebrow")) {
                const eyebrow = document.createElement("div");
                eyebrow.className = "practice-eyebrow";
                eyebrow.textContent = "PRACTICE";
                heading.parentNode.insertBefore(eyebrow, heading);
            }

            if (!header.querySelector(".practice-subtitle")) {
                const subtitle = document.createElement("p");
                subtitle.className = "practice-subtitle";
                subtitle.textContent = "Strengthen your knowledge one question at a time.";
                heading.insertAdjacentElement("afterend", subtitle);
            }
        }

        const nav = header.querySelector(".practice-mode-nav");
        if (nav) {
            const basicsLink = nav.querySelector('a[href*="/quiz/practice/"]');
            const proLink = nav.querySelector('a[href*="/quiz/"]');
            let expressLink = nav.querySelector('[data-practice-express-link="1"]');

            if (!expressLink) {
                expressLink = document.createElement("a");
                expressLink.href = "/quiz/practice/express/";
                expressLink.textContent = "Express";
                expressLink.className = "practice-mode active";
                expressLink.dataset.practiceExpressLink = "1";
                nav.insertBefore(expressLink, proLink || null);
            }

            if (basicsLink) {
                basicsLink.className = "practice-mode";
            }
            if (proLink && proLink !== expressLink) {
                proLink.className = "practice-mode";
            }
            expressLink.className = "practice-mode active";
        }
    }

    const filter = page.querySelector(".box.mb-3.p-3");
    if (filter) {
        filter.classList.add("practice-express-filter");
    }

    const stats = page.querySelector(".level.is-mobile");
    if (stats) {
        stats.classList.add("practice-express-stats");
    }

    const questionText = page.querySelector("#qText");
    const questionCard = questionText ? questionText.closest(".box") : null;
    if (questionCard) {
        questionCard.classList.add("practice-question-card");
        const choices = questionCard.querySelector("#choices");
        if (choices) {
            choices.classList.add("practice-options");
        }
    }

    const markExpressOptions = () => {
        page.querySelectorAll(".choice-item").forEach((option) => {
            option.classList.add("practice-express-option");
        });
    };

    markExpressOptions();

    const choices = page.querySelector("#choices");
    if (choices) {
        new MutationObserver(markExpressOptions).observe(choices, { childList: true });
    }

    if (!document.getElementById("practice-express-ui-style")) {
        const style = document.createElement("style");
        style.id = "practice-express-ui-style";
        style.textContent = `
            .practice-express-page {
                width: 100%;
                max-width: 1100px;
                margin: 0 auto;
                padding: 24px 20px 48px;
                box-sizing: border-box;
                background: var(--surface-color, #ffffff);
                border: 1px solid var(--border-color, #e5e7eb);
                border-radius: 14px;
                box-shadow: 0 8px 24px rgba(0, 0, 0, .06);
            }

            .practice-express-page .practice-page-header {
                display: flex;
                align-items: flex-end;
                justify-content: space-between;
                width: 100%;
                gap: 24px;
                margin: 0 0 22px;
                box-sizing: border-box;
            }

            .practice-express-page .practice-title {
                margin: 0;
                color: var(--text-color, #1f2937);
                font-size: clamp(1.8rem, 3vw, 2.35rem);
                line-height: 1.15;
                font-weight: 800;
            }

            .practice-express-page .practice-eyebrow {
                margin: 0 0 6px;
                color: var(--primary-color, #3273dc);
                font-size: .72rem;
                font-weight: 800;
                letter-spacing: .12em;
                text-transform: uppercase;
            }

            .practice-express-page .practice-subtitle {
                max-width: 650px;
                margin: 8px 0 0;
                color: var(--muted-text-color, #6b7280);
                font-size: .95rem;
                line-height: 1.6;
            }

            .practice-express-page .practice-mode-nav {
                display: flex;
                align-items: center;
                flex: 0 0 auto;
                gap: 0;
                padding: 0;
                border: 0;
                border-radius: 0;
                background: transparent;
                box-shadow: none;
                white-space: nowrap;
            }

            .practice-express-page .practice-mode {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-height: auto;
                padding: 0;
                border-radius: 0;
                color: var(--muted-text-color, #6b7280);
                font-size: .75rem;
                font-weight: 500;
                line-height: 1.5;
                text-decoration: none;
                white-space: nowrap;
                background: transparent !important;
                box-shadow: none !important;
            }

            .practice-express-page .practice-mode + .practice-mode::before {
                content: "|";
                display: inline-block;
                margin: 0 8px;
                color: var(--muted-text-color, #9ca3af);
            }

            .practice-express-page .practice-mode:hover {
                color: var(--text-color, #1f2937);
            }

            .practice-express-page .practice-mode.active {
                color: var(--primary-color, #3273dc) !important;
            }

            .practice-express-page > .box {
                border: 1px solid var(--border-color, #e5e7eb);
                border-radius: 10px;
                box-shadow: 0 4px 14px rgba(0, 0, 0, .05);
            }

            .practice-express-page .practice-express-filter {
                margin-bottom: 16px !important;
                padding: 14px !important;
            }

            .practice-express-page .practice-express-stats {
                margin-bottom: 10px !important;
            }

            .practice-express-page .practice-question-card {
                margin-top: 0;
                padding: 20px;
            }

            .practice-express-page .question-text {
                margin-bottom: 16px !important;
                color: var(--text-color, #1f2937);
                font-size: 1rem;
                line-height: 1.55;
            }

            .practice-express-page .practice-options {
                display: flex;
                flex-direction: column;
                gap: 7px;
                margin-bottom: 16px !important;
            }

            .practice-express-page .practice-express-option {
                display: flex;
                align-items: center;
                gap: 10px;
                min-height: 46px;
                padding: 7px 10px;
                border: 1px solid var(--border-color, #e5e7eb);
                border-radius: 8px;
                background: var(--surface-color, #ffffff);
                color: var(--text-color, #1f2937);
                font-size: .84rem;
                line-height: 1.35;
                box-sizing: border-box;
                cursor: pointer;
            }

            .practice-express-page .practice-express-option:hover {
                background: var(--surface-hover-color, #f8fafc);
                border-color: var(--primary-color, #3273dc);
            }

            .practice-express-page .practice-express-option input {
                width: 15px;
                height: 15px;
                margin: 0;
                flex: 0 0 auto;
            }

            .practice-express-page .choice-marker {
                display: inline-flex;
                flex: 0 0 34px;
                align-items: center;
                justify-content: center;
                width: 34px;
                height: 34px;
                box-sizing: border-box;
                border: 2px solid #cbd5e1;
                border-radius: 50%;
                color: #334e68;
                background: #fff;
                font-size: .88rem;
                font-weight: 600;
                line-height: 1;
            }

            .practice-express-page .choice-content {
                min-width: 0;
                flex: 1 1 auto;
            }

            .practice-express-page .button-group {
                display: flex;
                gap: 8px;
                align-items: center;
            }

            .practice-express-page .button-group .button {
                margin: 0;
            }

            @media (max-width: 700px) {
                .practice-express-page {
                    padding: 18px 14px 32px;
                    border-radius: 10px;
                }

                .practice-express-page .practice-page-header {
                    align-items: flex-start;
                    gap: 12px;
                }

                .practice-express-page .practice-title {
                    font-size: 1.65rem;
                }

                .practice-express-page .practice-subtitle {
                    font-size: .82rem;
                }
            }

            @media (max-width: 480px) {
                .practice-express-page .practice-mode {
                    font-size: .68rem;
                }

                .practice-express-page .practice-mode + .practice-mode::before {
                    margin: 0 5px;
                }

                .practice-express-page .practice-question-card {
                    padding: 14px;
                }
            }
        `;
        document.head.appendChild(style);
    }
});
