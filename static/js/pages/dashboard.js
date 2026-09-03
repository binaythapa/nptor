/* =========================================================
   NEPAL MENTOR
   STUDENT DASHBOARD JAVASCRIPT

   Responsibilities:
   - Exam track accordion
   - Cooldown countdown
   - Small dashboard interactions

   Global UI functionality stays in ui.js.
   ========================================================= */

(function () {

    "use strict";


    /* =====================================================
       DOM READY
       ===================================================== */

    document.addEventListener("DOMContentLoaded", function () {

        initializeTrackAccordions();

        initializeCountdowns();

    });


    /* =====================================================
       EXAM TRACK ACCORDION
       ===================================================== */

    function initializeTrackAccordions() {

        const trackButtons =
            document.querySelectorAll("[data-track-toggle]");

        if (!trackButtons.length) {
            return;
        }

        trackButtons.forEach(function (button) {

            button.addEventListener("click", function () {

                const trackCard =
                    button.closest(".exam-track-card");

                if (!trackCard) {
                    return;
                }

                const isOpen =
                    trackCard.classList.contains("is-open");

                /*
                 * Close other tracks.
                 *
                 * This keeps the dashboard clean and prevents
                 * the page from becoming unnecessarily long.
                 */
                document
                    .querySelectorAll(".exam-track-card.is-open")
                    .forEach(function (card) {

                        if (card !== trackCard) {
                            card.classList.remove("is-open");
                        }

                    });

                /*
                 * Toggle selected track.
                 */
                trackCard.classList.toggle(
                    "is-open",
                    !isOpen
                );

            });

        });

    }


    /* =====================================================
       COUNTDOWN
       ===================================================== */

    function initializeCountdowns() {

        const countdownElements =
            document.querySelectorAll(
                ".countdown-text[data-seconds]"
            );

        if (!countdownElements.length) {
            return;
        }

        countdownElements.forEach(function (element) {

            let seconds =
                parseInt(
                    element.dataset.seconds,
                    10
                );

            if (Number.isNaN(seconds)) {
                seconds = 0;
            }

            updateCountdownElement(
                element,
                seconds
            );

        });


        /*
         * Keep all cooldown timers synchronized.
         */
        window.setInterval(function () {

            countdownElements.forEach(function (element) {

                let seconds =
                    parseInt(
                        element.dataset.seconds,
                        10
                    );

                if (Number.isNaN(seconds)) {
                    seconds = 0;
                }

                if (seconds <= 0) {

                    updateCountdownElement(
                        element,
                        0
                    );

                    return;

                }

                seconds -= 1;

                element.dataset.seconds =
                    String(seconds);

                updateCountdownElement(
                    element,
                    seconds
                );

            });

        }, 1000);

    }


    /* =====================================================
       FORMAT COUNTDOWN
       ===================================================== */

    function updateCountdownElement(
        element,
        totalSeconds
    ) {

        if (totalSeconds <= 0) {

            element.textContent =
                "00:00:00";

            return;

        }


        const hours =
            Math.floor(
                totalSeconds / 3600
            );

        const minutes =
            Math.floor(
                (totalSeconds % 3600) / 60
            );

        const seconds =
            totalSeconds % 60;


        element.textContent =
            String(hours).padStart(2, "0")
            + ":"
            + String(minutes).padStart(2, "0")
            + ":"
            + String(seconds).padStart(2, "0");

    }


})();