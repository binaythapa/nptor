/* =========================================================
   NPTOR PRACTICE FILTERS

   Responsibilities:
   - Submit Domain / Category / Difficulty changes
   - Reset Category when Domain changes
   - Preserve normal GET filter URLs
   ========================================================= */

(function () {
    "use strict";

    function initPracticeFilters() {
        const form = document.querySelector(".practice-filter-form");

        if (!form) {
            return;
        }

        const domainSelect = form.querySelector("select[name='domain']");
        const categorySelect = form.querySelector("select[name='category']");

        form.addEventListener("change", function (event) {
            const select = event.target.closest("select");

            if (!select || !form.contains(select) || select.disabled) {
                return;
            }

            if (select === domainSelect && categorySelect) {
                categorySelect.value = "";
            }

            form.requestSubmit();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initPracticeFilters);
    } else {
        initPracticeFilters();
    }
})();
