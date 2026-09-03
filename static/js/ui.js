/* ============================================================
   NPTOR — SHARED UI
   ============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    () => {

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
            const total =
                getNum(
                    "practice_total"
                );

            const correct =
                getNum(
                    "practice_correct"
                );

            const accuracy =
                total > 0
                    ? Math.round(
                        (correct / total) *
                        100
                    )
                    : 0;

            if (practiceCounter) {
                practiceCounter.textContent =
                    `Matched: ${correct} / ${total}`;
            }

            if (practiceAccuracy) {
                practiceAccuracy.textContent =
                    `Accuracy: ${accuracy}%`;
            }
        }

        /*
         * Keep this global function because
         * practice templates may call it directly.
         */
        window.practiceAttempt =
            function ({
                correct,
                questionId,
                csrf
            }) {

                sessionStorage.setItem(
                    "practice_total",
                    getNum(
                        "practice_total"
                    ) + 1
                );

                if (correct) {
                    sessionStorage.setItem(
                        "practice_correct",
                        getNum(
                            "practice_correct"
                        ) + 1
                    );
                }

                updatePracticeUI();

                if (
                    questionId &&
                    csrf
                ) {
                    fetch(
                        "/quiz/practice/save/",
                        {
                            method: "POST",

                            headers: {
                                "X-CSRFToken":
                                    csrf,

                                "Content-Type":
                                    "application/x-www-form-urlencoded"
                            },

                            body:
                                `question_id=${encodeURIComponent(
                                    questionId
                                )}` +
                                `&is_correct=${encodeURIComponent(
                                    correct
                                )}`
                        }
                    ).catch(
                        (error) => {
                            console.error(
                                "Practice save failed:",
                                error
                            );
                        }
                    );
                }
            };

        window.resetPracticeStats =
            function () {

                sessionStorage.removeItem(
                    "practice_total"
                );

                sessionStorage.removeItem(
                    "practice_correct"
                );

                updatePracticeUI();
            };

        updatePracticeUI();


        /* ====================================================
           TRACK ACCORDION
           ==================================================== */

        document
            .querySelectorAll(
                ".track-header"
            )
            .forEach(
                (header) => {

                    if (
                        header.dataset
                            .accordionInitialized ===
                        "1"
                    ) {
                        return;
                    }

                    header.dataset
                        .accordionInitialized =
                        "1";

                    header.addEventListener(
                        "click",
                        () => {

                            const accordion =
                                header.closest(
                                    ".track-accordion"
                                );

                            if (
                                !accordion
                            ) {
                                return;
                            }

                            accordion.classList.toggle(
                                "is-open"
                            );

                            const expanded =
                                accordion.classList.contains(
                                    "is-open"
                                );

                            header.setAttribute(
                                "aria-expanded",
                                expanded
                                    ? "true"
                                    : "false"
                            );
                        }
                    );
                }
            );


        /* ====================================================
           COPY EMAIL
           ==================================================== */

        const copyBtn =
            document.querySelector(
                ".email-copy"
            );

        const toast =
            document.getElementById(
                "copy-toast"
            );

        if (
            copyBtn &&
            toast
        ) {

            copyBtn.addEventListener(
                "click",
                () => {

                    const email =
                        copyBtn.dataset.email;

                    if (!email) {
                        return;
                    }

                    navigator.clipboard
                        .writeText(
                            email
                        )
                        .then(
                            () => {
                                toast.classList.add(
                                    "show"
                                );

                                setTimeout(
                                    () => {
                                        toast.classList.remove(
                                            "show"
                                        );
                                    },
                                    2000
                                );
                            }
                        )
                        .catch(
                            (error) => {
                                console.error(
                                    "Unable to copy email:",
                                    error
                                );
                            }
                        );
                }
            );
        }

    }
);