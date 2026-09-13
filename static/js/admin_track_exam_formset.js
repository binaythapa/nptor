/* Dynamic TrackExam inline-formset rows. */
(function () {
    "use strict";

    function init() {
        const container = document.getElementById("track-exam-formset");
        const template = document.getElementById("track-exam-empty-form");
        const addButton = document.getElementById("add-track-exam");
        const total = document.getElementById("id_track_exams-TOTAL_FORMS");
        if (!container || !template || !addButton || !total) return;

        addButton.addEventListener("click", function () {
            const index = parseInt(total.value, 10) || 0;
            const html = template.innerHTML.replace(/__prefix__/g, index);
            container.insertAdjacentHTML("beforeend", html);
            total.value = index + 1;
            const rows = container.querySelectorAll(".track-exam-row");
            const row = rows[rows.length - 1];
            if (row) {
                const order = row.querySelector("[name$='-order']");
                if (order && !order.value) order.value = index + 1;
            }
        });
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
    else init();
})();
