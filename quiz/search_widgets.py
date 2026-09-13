from django.forms.widgets import Select, SelectMultiple
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe


class SearchableModelMultipleChoiceWidget(SelectMultiple):
    """Render only selected values and let JS fetch the remaining choices on demand."""

    def render(self, name, value, attrs=None, renderer=None):
        final_attrs = self.build_attrs(self.attrs, attrs)
        final_attrs["multiple"] = True
        final_attrs["data-admin-search-select"] = "true"
        final_attrs.setdefault("data-autocomplete-scope", "exams")

        selected_values = [str(item) for item in (self.format_value(value) or [])]
        selected_set = set(selected_values)
        options = []

        choices = self.choices
        if hasattr(choices, "queryset"):
            queryset = choices.queryset.filter(pk__in=selected_values)
            objects_by_id = {str(obj.pk): obj for obj in queryset}
            for selected in selected_values:
                obj = objects_by_id.get(selected)
                if obj is not None:
                    options.append((selected, str(obj)))
        else:
            for option_value, option_label in choices:
                if str(option_value) in selected_set:
                    options.append((str(option_value), str(option_label)))

        select_attrs = []
        for key, val in final_attrs.items():
            if val is True:
                select_attrs.append(key)
            elif val not in (False, None, ""):
                select_attrs.append('{}="{}"'.format(key, conditional_escape(val)))
        select_attrs.append('name="{}"'.format(conditional_escape(name)))
        select_attrs.append('style="display:none"')

        select_html = ["<select {}>".format(" ".join(select_attrs))]
        for option_value, option_label in options:
            select_html.append(
                '<option value="{}" selected>{}</option>'.format(
                    conditional_escape(option_value), conditional_escape(option_label)
                )
            )
        select_html.append("</select>")

        input_id = "{}_search".format(final_attrs.get("id", name))
        placeholder = final_attrs.get("data-search-placeholder", "Search exams...")
        return mark_safe(
            '<div class="admin-search-select" data-admin-search-select-ui="true">'
            '<input type="text" id="{}" class="admin-search-select-input" placeholder="{}" autocomplete="off" aria-label="Search exams">'
            '<div class="admin-search-select-selected" role="list" aria-live="polite"></div>'
            '<div class="admin-search-select-menu" role="listbox"></div>'
            '{}'</div>'.format(
                conditional_escape(input_id), conditional_escape(placeholder), "".join(select_html)
            )
        )


class SearchableModelChoiceWidget(Select):
    """Render one selected value and fetch other choices from the server as the user types."""

    def render(self, name, value, attrs=None, renderer=None):
        final_attrs = self.build_attrs(self.attrs, attrs)
        final_attrs["data-admin-search-select-single"] = "true"
        final_attrs.setdefault("data-autocomplete-scope", "exams")

        selected_value = "" if value in (None, "") else str(value)
        label = ""
        choices = self.choices
        if selected_value and hasattr(choices, "queryset"):
            obj = choices.queryset.filter(pk=selected_value).first()
            if obj is not None:
                label = str(obj)

        select_attrs = []
        for key, val in final_attrs.items():
            if val is True:
                select_attrs.append(key)
            elif val not in (False, None, ""):
                select_attrs.append('{}="{}"'.format(key, conditional_escape(val)))
        select_attrs.append('name="{}"'.format(conditional_escape(name)))
        select_html = '<select {} style="display:none">'.format(" ".join(select_attrs))
        if selected_value:
            select_html += '<option value="{}" selected>{}</option>'.format(
                conditional_escape(selected_value), conditional_escape(label)
            )
        select_html += "</select>"

        input_id = "{}_search".format(final_attrs.get("id", name))
        placeholder = final_attrs.get("data-search-placeholder", "Search exam...")
        return mark_safe(
            '<div class="admin-search-select-single" data-admin-search-select-single-ui="true">'
            '<input type="text" id="{}" class="admin-search-select-input" placeholder="{}" autocomplete="off" aria-label="Search exam">'
            '<div class="admin-search-select-selected" role="list" aria-live="polite"></div>'
            '<div class="admin-search-select-menu" role="listbox"></div>'
            '{}'</div>'.format(
                conditional_escape(input_id), conditional_escape(placeholder), select_html
            )
        )
