/* =========================================================
   NPTOR ADMIN EXAM SELECTOR
   Server-side prefix search for large Course/Track exam lists.
   ========================================================= */
(function () {
    "use strict";

    const endpoint = window.NPTOR_ADMIN_AUTOCOMPLETE_URL;
    const LIMIT = 20;
    const DEBOUNCE_MS = 250;

    if (!endpoint) return;

    function escapeHtml(value) {
        return String(value == null ? "" : value).replace(/[&<>\"']/g, function (ch) {
            return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[ch];
        });
    }

    function addStyles() {
        if (document.getElementById("nptor-admin-exam-selector-styles")) return;
        const style = document.createElement("style");
        style.id = "nptor-admin-exam-selector-styles";
        style.textContent = `
            .admin-exam-selector,.admin-search-select { position:relative; width:100%; }
            .admin-exam-selector-input,.admin-search-select-input { width:100%; box-sizing:border-box; padding:10px 12px; border:1px solid #d1d5db; border-radius:8px; font-size:14px; background:#fff; }
            .admin-exam-selector-input:focus,.admin-search-select-input:focus { outline:none; border-color:#2563eb; box-shadow:0 0 0 3px rgba(37,99,235,.12); }
            .admin-exam-selector-selected,.admin-search-select-selected { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
            .admin-exam-selector-chip,.admin-search-select-chip { display:inline-flex; align-items:center; gap:6px; max-width:100%; padding:6px 9px; border:1px solid #dbeafe; border-radius:999px; background:#eff6ff; color:#1e3a8a; font-size:.8rem; }
            .admin-exam-selector-chip span,.admin-search-select-chip span { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
            .admin-exam-selector-remove,.admin-search-select-remove { border:0; padding:0; background:transparent; color:#1d4ed8; cursor:pointer; font-size:16px; line-height:1; }
            .admin-exam-selector-menu,.admin-search-select-menu { position:absolute; left:0; right:0; top:calc(100% + 4px); z-index:10000; display:none; max-height:280px; overflow-y:auto; background:#fff; border:1px solid #d1d5db; border-radius:8px; box-shadow:0 12px 30px rgba(15,23,42,.14); }
            .admin-exam-selector-menu.is-open,.admin-search-select-menu.is-open { display:block; }
            .admin-exam-selector-option,.admin-search-select-option { display:block; width:100%; padding:10px 12px; border:0; border-bottom:1px solid #f1f5f9; background:#fff; color:#111827; text-align:left; cursor:pointer; }
            .admin-exam-selector-option:hover,.admin-search-select-option:hover { background:#eff6ff; }
            .admin-exam-selector-empty,.admin-search-select-empty { padding:10px 12px; color:#64748b; font-size:.82rem; }
        `;
        document.head.appendChild(style);
    }

    function attach(select) {
        if (select.dataset.adminExamSelectorReady === "1" || !select.multiple) return;
        const form = select.closest("form");
        if (!form) return;

        select.dataset.adminExamSelectorReady = "1";
        addStyles();

        const selected = new Map();
        Array.from(select.options).forEach(function (option) {
            if (option.selected) selected.set(String(option.value), option.textContent.trim());
        });

        let wrapper = select.closest(".admin-search-select");
        let input;
        let selectedContainer;
        let menu;
        let useExisting = Boolean(wrapper);

        if (useExisting) {
            input = wrapper.querySelector(".admin-search-select-input");
            selectedContainer = wrapper.querySelector(".admin-search-select-selected");
            menu = wrapper.querySelector(".admin-search-select-menu");
        } else {
            wrapper = document.createElement("div");
            wrapper.className = "admin-exam-selector";
            select.parentNode.insertBefore(wrapper, select);
            wrapper.appendChild(select);
            select.style.display = "none";
            input = document.createElement("input");
            input.type = "text";
            input.className = "admin-exam-selector-input";
            input.placeholder = select.dataset.searchPlaceholder || "Search exams...";
            input.autocomplete = "off";
            input.setAttribute("aria-label", "Search exams");
            wrapper.insertBefore(input, select);
            selectedContainer = document.createElement("div");
            selectedContainer.className = "admin-exam-selector-selected";
            wrapper.insertBefore(selectedContainer, select);
            menu = document.createElement("div");
            menu.className = "admin-exam-selector-menu";
            menu.setAttribute("role", "listbox");
            wrapper.insertBefore(menu, select);
        }

        if (!input || !selectedContainer || !menu) return;
        select.style.display = "none";
        if (!useExisting) {
            Array.from(select.options).forEach(function (option) {
                if (!option.selected) option.remove();
            });
        }

        function close() {
            menu.classList.remove("is-open");
            menu.innerHTML = "";
        }

        function syncSelect() {
            Array.from(select.options).forEach(function (option) {
                option.selected = selected.has(String(option.value));
            });
        }

        function renderSelected() {
            selectedContainer.innerHTML = "";
            selected.forEach(function (label, value) {
                const chip = document.createElement("span");
                chip.className = useExisting ? "admin-search-select-chip" : "admin-exam-selector-chip";
                const text = document.createElement("span");
                text.textContent = label;
                const remove = document.createElement("button");
                remove.type = "button";
                remove.className = useExisting ? "admin-search-select-remove" : "admin-exam-selector-remove";
                remove.textContent = "×";
                remove.setAttribute("aria-label", "Remove " + label);
                remove.addEventListener("click", function () {
                    selected.delete(value);
                    Array.from(select.options).forEach(function (option) {
                        if (String(option.value) === value) option.remove();
                    });
                    syncSelect();
                    renderSelected();
                    input.focus();
                });
                chip.appendChild(text);
                chip.appendChild(remove);
                selectedContainer.appendChild(chip);
            });
        }

        function addResult(item) {
            const value = String(item.id);
            if (selected.has(value)) return;
            selected.set(value, item.label || "");
            select.add(new Option(item.label || "", value, true, true));
            syncSelect();
            renderSelected();
            input.value = "";
            close();
            input.focus();
        }

        function trackExamIds() {
            const trackContainer = select.closest("#track-exam-formset");
            if (!trackContainer) return [];
            return Array.from(trackContainer.querySelectorAll("select[name$='-exam']"))
                .map(function (examSelect) { return examSelect.value; })
                .filter(Boolean)
                .filter(function (value, index, values) { return values.indexOf(value) === index; });
        }

        let timer = null;
        let requestId = 0;
        function search(query) {
            clearTimeout(timer);
            close();
            if (!query) return;
            timer = setTimeout(function () {
                const current = ++requestId;
                const params = new URLSearchParams({scope: "exams", q: query});
                const organization = select.dataset.autocompleteOrganization;
                if (organization) params.set("organization", organization);
                if (select.dataset.autocompleteTrackExamsOnly === "true") {
                    const ids = trackExamIds();
                    if (ids.length) params.set("ids", ids.join(","));
                    else {
                        menu.innerHTML = '<div class="admin-search-select-empty">Add an included Track Exam first</div>';
                        menu.classList.add("is-open");
                        return;
                    }
                }
                fetch(endpoint + "?" + params.toString(), {headers: {"X-Requested-With": "XMLHttpRequest"}})
                    .then(function (response) { return response.ok ? response.json() : {results: []}; })
                    .then(function (data) {
                        if (current !== requestId) return;
                        const results = Array.isArray(data.results) ? data.results.slice(0, LIMIT).filter(function (item) {
                            return !selected.has(String(item.id));
                        }) : [];
                        const optionClass = useExisting ? "admin-search-select-option" : "admin-exam-selector-option";
                        const emptyClass = useExisting ? "admin-search-select-empty" : "admin-exam-selector-empty";
                        menu.innerHTML = results.length ? results.map(function (item, index) {
                            return '<button type="button" class="' + optionClass + '" data-index="' + index + '">' + escapeHtml(item.label) + '</button>';
                        }).join("") : '<div class="' + emptyClass + '">No matching exams</div>';
                        menu.classList.add("is-open");
                        menu.querySelectorAll("button").forEach(function (button, index) {
                            button.addEventListener("mousedown", function (event) { event.preventDefault(); });
                            button.addEventListener("click", function () { if (results[index]) addResult(results[index]); });
                        });
                    })
                    .catch(function () {
                        if (current === requestId) {
                            menu.innerHTML = '<div class="admin-search-select-empty">Unable to search right now</div>';
                            menu.classList.add("is-open");
                        }
                    });
            }, DEBOUNCE_MS);
        }

        input.addEventListener("input", function () { search(input.value.trim()); });
        input.addEventListener("keydown", function (event) { if (event.key === "Escape") close(); });
        document.addEventListener("click", function (event) { if (!wrapper.contains(event.target)) close(); });
        renderSelected();
    }

    function init(root) {
        (root || document).querySelectorAll("select[multiple][name$='exams']").forEach(attach);
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
