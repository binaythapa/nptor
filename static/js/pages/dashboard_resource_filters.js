document.addEventListener("DOMContentLoaded", function () {
    const filters = document.querySelectorAll("[data-dashboard-filter]");
    const search = document.querySelector("[data-dashboard-search]");
    const cards = document.querySelectorAll("[data-learning-card]");
    const empty = document.querySelector("[data-dashboard-empty]");

    function applyFilters() {
        const active = document.querySelector("[data-dashboard-filter].is-active")?.dataset.dashboardFilter || "all";
        const query = (search?.value || "").trim().toLowerCase();
        let visible = 0;
        cards.forEach(function (card) {
            const type = card.dataset.learningType;
            const name = card.dataset.learningName || "";
            const typeMatches = active === "all" || type === active.slice(0, -1);
            const searchMatches = !query || name.includes(query);
            card.hidden = !(typeMatches && searchMatches);
            if (typeMatches && searchMatches) visible += 1;
        });
        if (empty) empty.hidden = visible !== 0;
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
