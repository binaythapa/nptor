document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-formset-prefix]").forEach(function (container) {
        var prefix = container.dataset.formsetPrefix;
        var totalForms = document.getElementById("id_" + prefix + "-TOTAL_FORMS");
        var rows = container.querySelector("[data-formset-rows]");
        var template = container.querySelector("[data-empty-form-template]");
        var addButton = container.querySelector("[data-add-form]");

        if (!totalForms || !rows || !template || !addButton) {
            return;
        }

        function bindDeleteControl(row) {
            var checkbox = row.querySelector('input[name$="-DELETE"]');
            if (!checkbox) {
                return;
            }

            function updateVisibility() {
                row.classList.toggle("is-deleted", checkbox.checked);
            }

            checkbox.addEventListener("change", updateVisibility);
            updateVisibility();
        }

        rows.querySelectorAll("[data-formset-row]").forEach(bindDeleteControl);

        addButton.addEventListener("click", function () {
            var index = parseInt(totalForms.value, 10);
            var html = template.innerHTML.replace(/__prefix__/g, index);
            var wrapper = document.createElement("div");
            wrapper.innerHTML = html.trim();
            var row = wrapper.firstElementChild;

            if (!row) {
                return;
            }

            rows.appendChild(row);
            totalForms.value = index + 1;
            bindDeleteControl(row);

            var category = row.querySelector("select");
            if (category) {
                category.focus();
            }
        });
    });
});
