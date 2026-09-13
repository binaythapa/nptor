/* NPTOR single-value server-side exam autocomplete. */
(function () {
    "use strict";

    const endpoint = window.NPTOR_ADMIN_AUTOCOMPLETE_URL;
    const DEBOUNCE_MS = 250;

    if (!endpoint) return;

    function escapeHtml(value) {
        return String(value == null ? "" : value).replace(/[&<>\"']/g, function (ch) {
            return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[ch];
        });
    }

    function attach(wrapper) {
        if (wrapper.dataset.ready === "1") return;
        const select = wrapper.querySelector("select[data-admin-search-select-single]");
        const input = wrapper.querySelector(".admin-search-select-input");
        const selectedBox = wrapper.querySelector(".admin-search-select-selected");
        const menu = wrapper.querySelector(".admin-search-select-menu");
        if (!select || !input || !selectedBox || !menu) return;
        wrapper.dataset.ready = "1";

        let selected = select.value ? {
            id: String(select.value),
            label: select.options[select.selectedIndex] ? select.options[select.selectedIndex].textContent.trim() : ""
        } : null;
        let timer = null;
        let requestId = 0;

        function close() {
            menu.classList.remove("is-open");
            menu.innerHTML = "";
        }

        function renderSelected() {
            selectedBox.innerHTML = "";
            if (!selected) return;
            const chip = document.createElement("span");
            chip.className = "admin-search-select-chip";
            const text = document.createElement("span");
            text.textContent = selected.label;
            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "admin-search-select-remove";
            remove.textContent = "×";
            remove.setAttribute("aria-label", "Remove " + selected.label);
            remove.addEventListener("click", function () {
                selected = null;
                select.innerHTML = "";
                select.value = "";
                renderSelected();
                input.focus();
            });
            chip.appendChild(text);
            chip.appendChild(remove);
            selectedBox.appendChild(chip);
        }

        function choose(item) {
            selected = {id: String(item.id), label: item.label || ""};
            select.innerHTML = "";
            select.add(new Option(selected.label, selected.id, true, true));
            renderSelected();
            input.value = "";
            close();
            input.focus();
        }

        function search(query) {
            clearTimeout(timer);
            close();
            if (!query) return;
            timer = setTimeout(function () {
                const current = ++requestId;
                const params = new URLSearchParams({scope: "exams", q: query});
                const organization = select.dataset.autocompleteOrganization;
                if (organization) params.set("organization", organization);
                fetch(endpoint + "?" + params.toString(), {headers: {"X-Requested-With": "XMLHttpRequest"}})
                    .then(function (response) { return response.ok ? response.json() : {results: []}; })
                    .then(function (data) {
                        if (current !== requestId) return;
                        const results = (data.results || []).filter(function (item) {
                            return !selected || String(item.id) !== selected.id;
                        });
                        menu.innerHTML = results.length ? results.map(function (item, index) {
                            return '<button type="button" class="admin-search-select-option" data-index="' + index + '">' + escapeHtml(item.label) + '</button>';
                        }).join("") : '<div class="admin-search-select-empty">No matching exams</div>';
                        menu.classList.add("is-open");
                        menu.querySelectorAll("button").forEach(function (button, index) {
                            button.addEventListener("mousedown", function (event) { event.preventDefault(); });
                            button.addEventListener("click", function () { if (results[index]) choose(results[index]); });
                        });
                    });
            }, DEBOUNCE_MS);
        }

        input.addEventListener("input", function () { search(input.value.trim()); });
        input.addEventListener("keydown", function (event) { if (event.key === "Escape") close(); });
        document.addEventListener("click", function (event) { if (!wrapper.contains(event.target)) close(); });
        renderSelected();
    }

    function init(root) {
        (root || document).querySelectorAll("[data-admin-search-select-single-ui='true']").forEach(attach);
    }

    function start() {
        init(document);
        const observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                mutation.addedNodes.forEach(function (node) {
                    if (node.nodeType === 1) init(node);
                });
            });
        });
        observer.observe(document.body, {childList: true, subtree: true});
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
    else start();
})();
