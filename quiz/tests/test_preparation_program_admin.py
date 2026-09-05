from django.contrib import admin
from django.test import TestCase

from quiz.admin_government_catalog import PreparationProgramAdmin
from quiz.models import ContentVertical, PreparationProgram


class PreparationProgramAdminTests(TestCase):
    def test_preparation_program_is_registered_with_expected_management_options(self):
        self.assertIn(PreparationProgram, admin.site._registry)
        registered = admin.site._registry[PreparationProgram]
        self.assertIsInstance(registered, PreparationProgramAdmin)
        self.assertIn("name", registered.search_fields)
        self.assertIn("code", registered.search_fields)
        self.assertIn("content_vertical", registered.list_filter)
        self.assertIn("country", registered.list_filter)
        self.assertIn("courses", registered.filter_horizontal)
        self.assertIn("exams", registered.filter_horizontal)
        self.assertEqual(registered.prepopulated_fields, {"slug": ("name",)})

    def test_admin_can_construct_program_from_catalog_model(self):
        vertical = ContentVertical.objects.create(
            name="Academic Exam",
            code="academic-admin-test",
            vertical_type=ContentVertical.ACADEMIC_EXAM,
        )
        program = PreparationProgram.objects.create(
            content_vertical=vertical,
            name="IOE Entrance Preparation",
            code="ioe-entrance",
            slug="ioe-entrance-admin-test",
        )
        self.assertEqual(str(program), "IOE Entrance Preparation")
