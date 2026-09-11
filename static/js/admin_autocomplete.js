/* =========================================================
   NPTOR ADMIN AUTOCOMPLETE
   Server-side prefix suggestions for admin search fields.
   ========================================================= */
(function () {
    "use strict";

    const endpoint = window.NPTOR_ADMIN_AUTOCOMPLETE_URL;
    const LIMIT = 20;
    const DEBOUNCE_MS = 250;

    if (!endpoint) return;

    function inferScope() {
        const path = window.location.pathname;
        if (path.includes("/accounts/admin/users")) return "users";
        if (path.includes("/courses/admin/")) return "courses";
        if (path.includes("/dashboard/admin/tracks")) return "tracks";
        if (path.includes("/dashboard/admin/exams")) return "exams";
        if (path.includes("/dashboard/questions")) return "questions";
        if (path.includes("/dashboard/admin/coupons")) return "coupons";
        if (path.includes("/notifications")) return "notifications";
        return null;
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value).replace(/[&<>\"']/g, function (ch) {
            return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[ch];
        });
    }

    function attach(input) {
        if (input.dataset.adminAutocompleteReady === "1") return;
        const form = input.closest("form");
        if (!form) return;

        const scope = input.dataset.autocompleteScope || form.dataset.autocompleteScope || inferScope();
        if (!scope) return;

        input.dataset.adminAutocompleteReady = "1";
        input.setAttribute("autocomplete", "off");
        const wrapper = document.createElement("div");
        wrapper.className = "admin-autocomplete-wrapper";
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        const menu = document.createElement("div");
        menu.className = "admin-autocomplete-menu";
        menu.setAttribute("role", "listbox");
        wrapper.appendChild(menu);

        let timer = null;
        let requestId = 0;
        let results = [];
        let activeIndex = -1;

        function close() {
            menu.classList.remove("is-open");
            menu.innerHTML = "";
            results = [];
            activeIndex = -1;
        }

        function setActive(index) {
            const options = menu.querySelectorAll(".admin-autocomplete-option");
            options.forEach(function (option) { option.classList.remove("is-active"); });
            activeIndex = index;
            if (activeIndex >= 0 && options[activeIndex]) {
                options[activeIndex].classList.add("is-active");
                options[activeIndex].scrollIntoView({block: "nearest"});
            }
        }

        function choose(index) {
            if (!results[index]) return;
            input.value = results[index].label || "";
            close();
            if (input.dataset.autocompleteSubmit === "true") form.submit();
        }

        function render(items) {
            results = items.slice(0, LIMIT);
            activeIndex = -1;
            if (!results.length) {
                menu.innerHTML = '<div class="admin-autocomplete-empty">No matching records</div>';
            } else {
                menu.innerHTML = results.map(function (item, index) {
                    return '<button type="button" class="admin-autocomplete-option" role="option" data-index="' + index + '">' +
                        '<span>' + escapeHtml(item.label) + '</span>' +
                        (item.subtitle ? '<small>' + escapeHtml(item.subtitle) + '</small>' : '') +
                        '</button>';
                }).join("");
                menu.querySelectorAll(".admin-autocomplete-option").forEach(function (button, index) {
                    button.addEventListener("mousedown", function (event) { event.preventDefault(); });
                    button.addEventListener("click", function () { choose(index); });
                });
            }
            menu.classList.add("is-open");
        }

        input.addEventListener("input", function () {
            const q = input.value.trim();
            clearTimeout(timer);
            close();
            if (!q) return;
            timer = setTimeout(function () {
                const current = ++requestId;
                const url = endpoint + "?scope=" + encodeURIComponent(scope) + "&q=" + encodeURIComponent(q);
                fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
                    .then(function (response) { return response.ok ? response.json() : {results: []}; })
                    .then(function (data) {
                        if (current !== requestId) return;
                        render(Array.isArray(data.results) ? data.results : []);
                    })
                    .catch(function () {
                        if (current === requestId) render([]);
                    });
            }, DEBOUNCE_MS);
        });

        input.addEventListener("keydown", function (event) {
            if (!menu.classList.contains("is-open") || !results.length) {
                if (event.key === "Escape") close();
                return;
            }
            if (event.key === "ArrowDown") {
                event.preventDefault();
                setActive(activeIndex < results.length - 1 ? activeIndex + 1 : 0);
            } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setActive(activeIndex > 0 ? activeIndex - 1 : results.length - 1);
            } else if (event.key === "Enter" && activeIndex >= 0) {
                event.preventDefault();
                choose(activeIndex);
            } else if (event.key === "Escape") {
                event.preventDefault();
                close();
            }
        });

        document.addEventListener("click", function (event) {
            if (!wrapper.contains(event.target)) close();
        });
    }

    function init() {
        document.querySelectorAll("input[name='q']").forEach(attach);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
