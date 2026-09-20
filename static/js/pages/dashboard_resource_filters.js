document.addEventListener("DOMContentLoaded", function () {
    const filters = document.querySelectorAll("[data-dashboard-filter]");
    const search = document.querySelector("[data-dashboard-search]");
    const cards = document.querySelectorAll("[data-dashboard-grid] [data-learning-card]");
    const empty = document.querySelector("[data-dashboard-empty]");

    // Exams are not individually subscribable resources. Keep them out of
    // the My Learning resource filters even if older markup contains the tab.
    const examFilter = document.querySelector('[data-dashboard-filter="exams"]');
    if (examFilter && !document.querySelector('[data-dashboard-grid] [data-learning-card][data-learning-type="exam"]')) {
        examFilter.hidden = true;
        examFilter.setAttribute("aria-hidden", "true");
    }

    document.querySelectorAll("[data-dashboard-grid] .learning-source").forEach(function (badge) {
        if (badge.textContent.trim().toLowerCase() === "assigned") {
            badge.classList.add("learning-source-organization");
            badge.textContent = "Assigned by Organization";
            badge.setAttribute("title", "This resource was assigned to you by your organization.");
        }
    });

    function applyFilters() {
        const active = document.querySelector("[data-dashboard-filter].is-active")?.dataset.dashboardFilter || "all";
        const query = (search?.value || "").trim().toLowerCase();
        let visible = 0;
        cards.forEach(function (card) {
            const type = card.dataset.learningType;
            const name = card.dataset.learningName || "";
            const typeMatches = active === "all" || type === active.slice(0, -1);
            const searchMatches = !query || name.includes(query);
            const matches = typeMatches && searchMatches;
            card.hidden = !matches;
            card.style.display = matches ? "" : "none";
            if (matches) visible += 1;
        });
        if (empty) {
            const hasResults = visible !== 0;
            empty.hidden = hasResults;
            empty.style.display = hasResults ? "none" : "flex";
        }
    }

    filters.forEach(function (button) {
        button.addEventListener("click", function () {
            filters.forEach(function (item) {
                item.classList.remove("is-active");
                item.setAttribute("aria-selected", "false");
            });
            button.classList.add("is-active");
            button.setAttribute("aria-selected", "true");
            applyFilters();
        });
    });
    if (search) search.addEventListener("input", applyFilters);
    applyFilters();
});
