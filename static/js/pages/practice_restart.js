/*
 * Course-practice restart handling.
 *
 * The existing reset endpoint clears the practice session and redirects to
 * the generic practice page. For course practice, perform that reset through
 * fetch first, then explicitly return to the original course/lesson context.
 */
(function () {
    "use strict";

    document.addEventListener("click", async function (event) {
        const link = event.target.closest("[data-practice-restart]");
        if (!link) {
            return;
        }

        event.preventDefault();

        if (link.dataset.restarting === "1") {
            return;
        }

        const course = link.dataset.course || "";
        const lesson = link.dataset.lesson || "";
        const resetUrl = link.href;

        if (!course || !lesson || !resetUrl) {
            window.location.assign(link.href);
            return;
        }

        link.dataset.restarting = "1";
        link.setAttribute("aria-disabled", "true");

        try {
            const response = await fetch(resetUrl, {
                method: "GET",
                credentials: "same-origin",
                redirect: "manual",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            });

            // The reset view normally returns a redirect. A same-origin
            // response is sufficient evidence that the session was reset;
            // the destination is intentionally controlled below.
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
