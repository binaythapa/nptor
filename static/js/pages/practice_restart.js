/*
 * Restart practice with a clean session.
 *
 * Course-practice completion markup may come from either the dedicated
 * completion partial or the inline completion block. Support both forms:
 * explicit data attributes and a completion-card link while the current URL
 * contains course/lesson context.
 */
(function () {
    "use strict";

    document.addEventListener("click", async function (event) {
        const link = event.target.closest("a.practice-btn-secondary, [data-practice-restart]");
        if (!link) {
            return;
        }

        const completionCard = link.closest(".practice-completed-card");
        const isRestartLink = link.matches("[data-practice-restart]") ||
            (completionCard && /practice again/i.test(link.textContent || ""));

        if (!isRestartLink) {
            return;
        }

        const currentUrl = new URL(window.location.href);
        const course = link.dataset.course || currentUrl.searchParams.get("course") || "";
        const lesson = link.dataset.lesson || currentUrl.searchParams.get("lesson") || "";

        if (!course || !lesson) {
            return;
        }

        event.preventDefault();

        if (link.dataset.restarting === "1") {
            return;
        }

        const resetUrl = new URL(link.href || "/quiz/practice/", window.location.origin);
        resetUrl.searchParams.set("reset", "1");
        resetUrl.searchParams.set("course", course);
        resetUrl.searchParams.set("lesson", lesson);

        link.dataset.restarting = "1";
        link.setAttribute("aria-disabled", "true");

        try {
            const response = await fetch(resetUrl.toString(), {
                method: "GET",
                credentials: "same-origin",
                redirect: "manual",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            });

            if (response.type === "opaqueredirect" || response.status === 302 || response.ok) {
                const target = new URL("/quiz/practice/", window.location.origin);
                target.searchParams.set("course", course);
                target.searchParams.set("lesson", lesson);
                window.location.assign(target.toString());
                return;
            }

            throw new Error("Practice session reset failed.");
        } catch (error) {
            console.error("Unable to restart course practice:", error);
            link.dataset.restarting = "";
            link.removeAttribute("aria-disabled");
            alert("Unable to restart practice. Please try again.");
        }
    });
})();
