from django import forms
from django.test import SimpleTestCase

from quiz.forms.widgets import SearchableModelMultipleChoiceWidget


class SearchableExamSelectorTests(SimpleTestCase):
    def test_widget_renders_search_control_without_rendering_entire_choice_list(self):
        class Form(forms.Form):
            exams = forms.MultipleChoiceField(
                choices=[
                    ("1", "Test Exam"),
                    ("2", "Another Exam"),
                ],
                widget=SearchableModelMultipleChoiceWidget(
                    attrs={"data-autocomplete-scope": "exams"}
                ),
            )

        html = Form(initial={"exams": ["1"]}).as_p()

        self.assertIn('data-admin-search-select="true"', html)
        self.assertIn('data-autocomplete-scope="exams"', html)
        self.assertIn('placeholder="Search exams..."', html)
        self.assertIn('value="1"', html)
        self.assertIn("Test Exam", html)
        self.assertNotIn('value="2"', html)

    def test_widget_preserves_multiple_selected_values(self):
        class Form(forms.Form):
            exams = forms.MultipleChoiceField(
                choices=[("1", "First"), ("2", "Second"), ("3", "Third")],
                widget=SearchableModelMultipleChoiceWidget(),
            )

        html = Form(initial={"exams": ["1", "3"]}).as_p()

        self.assertIn('value="1"', html)
        self.assertIn('value="3"', html)
        self.assertNotIn('value="2"', html)
