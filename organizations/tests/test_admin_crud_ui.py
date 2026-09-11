from pathlib import Path

from django.test import SimpleTestCase


class AdminCrudUiRegressionTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(__file__).resolve().parents[2]

    def read(self, relative_path):
        return (self.root / relative_path).read_text(encoding="utf-8")

    def test_shared_crud_stylesheet_is_loaded_by_both_admin_shells(self):
        platform_base = self.read("templates/layouts/admin/base_admin.html")
        organization_base = self.read("templates/organizations/admin/base.html")

        self.assertIn("css/admin-crud.css", platform_base)
        self.assertIn("css/admin-crud-overrides.css", platform_base)
        self.assertIn("css/admin-crud.css", organization_base)
        self.assertIn("css/admin-crud-overrides.css", organization_base)

    def test_crud_styles_cover_core_admin_components(self):
        css = self.read("static/css/admin-crud.css")

        for selector in (
            ".admin-crud-header",
            ".admin-crud-kpis",
            ".admin-crud-filter",
            ".admin-crud-table-wrap",
            ".admin-table-actions",
            ".admin-form-actions",
            ".admin-status",
        ):
            self.assertIn(selector, css)

    def test_question_dashboard_gets_compact_five_card_grid(self):
        overrides = self.read("static/css/admin-crud-overrides.css")
        self.assertIn(".dashboard-header + .columns.is-multiline", overrides)
        self.assertIn("grid-template-columns: repeat(5, minmax(0, 1fr))", overrides)

    def test_organization_crud_templates_use_the_existing_admin_shell(self):
        template_paths = (
            "templates/organizations/admin/categories/list.html",
            "templates/organizations/admin/categories/create.html",
            "templates/organizations/admin/categories/edit.html",
            "templates/organizations/admin/tracks/list.html",
            "templates/organizations/admin/tracks/create.html",
            "templates/organizations/admin/tracks/edit.html",
            "templates/organizations/admin/exams/list.html",
            "templates/organizations/admin/exams/create.html",
            "templates/organizations/admin/exams/edit.html",
        )
        for relative_path in template_paths:
            self.assertIn(
                '{% extends "organizations/admin/base.html" %}',
                self.read(relative_path),
                relative_path,
            )
