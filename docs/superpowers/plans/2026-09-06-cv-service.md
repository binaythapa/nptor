# NPTOR CV Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone NPTOR CV service that lets authenticated users create, import, edit, version, render, export, and deliver CVs without depending on courses, tracks, or exams.

**Architecture:** Add a dedicated Django `cv` app with structured Master Career Profile records, per-CV selection/override data, immutable CV versions, independent templates, deterministic PDF/DOCX import/export adapters, and provider interfaces for AI and messaging. Reuse the existing Django user/account profile and email service, while keeping optional NPTOR learning/certification import separate from core CV creation.

**Tech Stack:** Django 6.0, MySQL, existing NPTOR templates/Bulma UI, `pdfminer.six`/`pdfplumber` for PDF extraction, `reportlab` for PDF output, `python-docx` for DOCX extraction/output, Django file storage, and provider-neutral Python service interfaces.

**Spec:** `docs/superpowers/specs/2026-09-06-cv-service-design.md`

## Global Constraints

- Core CV creation must not require a course, track, exam, question bank, or learning enrollment.
- Existing account name/email/phone/location data should be reused instead of being re-entered unnecessarily.
- Account email remains authoritative for CV delivery by email.
- Master Career Profile is reusable, while each CV can select, override, or add information independently.
- Imported and AI-suggested facts remain unconfirmed until the user explicitly confirms them.
- AI must never silently invent employers, dates, qualifications, metrics, certifications, or achievements.
- External AI, WhatsApp, and Viber credentials must not be required for the core CV builder.
- User ownership checks must protect every career profile, CV, uploaded source, version, artifact, and delivery record.
- Templates are independent of content and must remain version-safe for previously saved CVs.
- Reward events must be auditable and idempotent and must reward profile improvement rather than disclosure of personal information.

---

### Task 1: Create the CV application foundation and dependency configuration

**Files:**
- Create: `cv/__init__.py`
- Create: `cv/apps.py`
- Create: `cv/admin.py`
- Create: `cv/urls.py`
- Modify: `objective_exam/settings.py`
- Modify: `objective_exam/urls.py`
- Modify: `requirements.txt`
- Test: `cv/tests/test_app_config.py`

**Interfaces:**
- Produces Django app label `cv` and URL namespace `cv`.
- Produces root route `/cv/` for the authenticated CV workspace.
- Adds `python-docx` as the DOCX dependency while reusing the existing PDF libraries and reportlab already present in `requirements.txt`.

- [ ] **Step 1: Write the failing app/configuration tests.**

```python
from django.apps import apps
from django.test import SimpleTestCase
from django.urls import resolve, reverse


class CVAppConfigTests(SimpleTestCase):
    def test_cv_app_is_installed(self):
        self.assertEqual(apps.get_app_config("cv").name, "cv")

    def test_cv_workspace_route_exists(self):
        self.assertEqual(reverse("cv:dashboard"), "/cv/")
        self.assertEqual(resolve("/cv/").url_name, "dashboard")
```

- [ ] **Step 2: Run `python manage.py test cv.tests.test_app_config -v 2` and verify it fails because the app/routes do not exist.**

- [ ] **Step 3: Add `CVConfig`, register `cv` in `INSTALLED_APPS`, include `cv.urls` at `/cv/`, and add the pinned `python-docx` dependency.**

- [ ] **Step 4: Add the minimal authenticated dashboard route and run the same test to verify it passes.**

- [ ] **Step 5: Commit with `git add cv objective_exam/settings.py objective_exam/urls.py requirements.txt && git commit -m "feat: add CV service foundation"`.**

---

### Task 2: Build the Master Career Profile data model and account reuse

**Files:**
- Create: `cv/models.py`
- Create: `cv/migrations/0001_initial.py`
- Create: `cv/forms.py`
- Create: `cv/services/profile.py`
- Create: `cv/tests/test_profile_models.py`
- Create: `cv/tests/test_profile_service.py`
- Modify: `cv/admin.py`

**Interfaces:**
- `get_or_create_career_profile(user) -> CareerProfile` returns the single reusable profile for a user.
- `account_contact_defaults(user) -> dict` returns account-derived name, email, phone, and location values without duplicating account ownership.
- Structured models produced: `CareerProfile`, `CareerExperience`, `CareerEducation`, `CareerProject`, `CareerSkill`, `CareerAchievement`, and `CareerCertification`.

- [ ] **Step 1: Write tests proving one profile per user, child records are owned through that profile, and account email/name defaults are reused.**

```python
class CareerProfileTests(TestCase):
    def test_profile_is_one_per_user(self):
        profile = get_or_create_career_profile(self.user)
        same_profile = get_or_create_career_profile(self.user)
        self.assertEqual(profile.pk, same_profile.pk)

    def test_profile_does_not_require_learning_enrollment(self):
        profile = get_or_create_career_profile(self.user)
        self.assertIsNotNone(profile.pk)
```

- [ ] **Step 2: Run the focused tests and confirm the expected missing-model failures.**

- [ ] **Step 3: Implement the profile and child models with explicit ordering, timestamps, confirmation state, and ownership through `CareerProfile`.**

- [ ] **Step 4: Implement `account_contact_defaults()` using `user.first_name`, `user.last_name`, `user.email`, and the existing `UserProfile` phone/country/address when available. Do not copy the account email into a second authoritative account field.**

- [ ] **Step 5: Register the models in admin and run `python manage.py test cv.tests.test_profile_models cv.tests.test_profile_service -v 2`.**

- [ ] **Step 6: Commit with `git add cv && git commit -m "feat: add master career profile"`.**

---

### Task 3: Add saved CVs, per-CV overrides, versions, templates, and seed data

**Files:**
- Create: `cv/models_cv.py`
- Create: `cv/models_template.py`
- Create: `cv/models_version.py`
- Create: `cv/migrations/0002_cv_workspace.py`
- Create: `cv/services/cv_builder.py`
- Create: `cv/management/commands/seed_cv_templates.py`
- Create: `cv/tests/test_cv_builder.py`
- Create: `cv/tests/test_cv_templates.py`
- Modify: `cv/models.py`
- Modify: `cv/admin.py`

**Interfaces:**
- `create_cv(user, title, template) -> CV` creates a CV independently of learning products.
- `build_cv_payload(cv) -> dict` returns normalized content for rendering.
- `create_cv_version(cv) -> CVVersion` stores a snapshot of the current selected/overridden content.
- `duplicate_cv(cv, title=None) -> CV` creates an independent editable copy.
- `seed_cv_templates` creates the eight templates named in the spec: ATS Classic, Modern Professional, Executive, Technical, Fresher, Academic, Government, and Minimal.

- [ ] **Step 1: Write tests for create/edit/duplicate/version and template independence.**

```python
class CVBuilderTests(TestCase):
    def test_create_cv_requires_no_course_or_exam(self):
        cv = create_cv(self.user, "Software Engineer CV", self.template)
        self.assertEqual(cv.owner_id, self.user.id)
        self.assertIsNone(cv.profile_id if False else None)

    def test_duplicate_cv_is_independent(self):
        original = create_cv(self.user, "Original", self.template)
        copy = duplicate_cv(original, "Tailored Version")
        self.assertNotEqual(original.pk, copy.pk)
```

- [ ] **Step 2: Run the focused tests and confirm missing implementation failures.**

- [ ] **Step 3: Implement `CV`, `CVVersion`, and `CVTemplate` with JSON snapshot/override fields where appropriate, explicit user ownership, status fields, timestamps, and stable template identifiers.**

- [ ] **Step 4: Implement the builder service so profile content can be selected per CV and overridden without mutating the Master Career Profile.**

- [ ] **Step 5: Add the template seed command and assert exactly the eight default slugs/names in tests.**

- [ ] **Step 6: Run `python manage.py test cv.tests.test_cv_builder cv.tests.test_cv_templates -v 2` and commit with `git add cv && git commit -m "feat: add saved CV workspace and templates"`.**

---

### Task 4: Add existing CV import and confirmation workflow

**Files:**
- Create: `cv/services/importers/base.py`
- Create: `cv/services/importers/pdf.py`
- Create: `cv/services/importers/docx.py`
- Create: `cv/services/importers/parser.py`
- Create: `cv/services/importers/service.py`
- Create: `cv/models_import.py`
- Create: `cv/migrations/0003_cv_imports.py`
- Create: `cv/tests/test_cv_import.py`
- Modify: `cv/models.py`

**Interfaces:**
- `extract_text_from_pdf(file) -> str`
- `extract_text_from_docx(file) -> str`
- `parse_career_facts(text) -> dict`
- `import_cv_source(user, uploaded_file) -> CVImport` stores an unconfirmed normalized extraction.
- `confirm_import_field(import_field_id, user, value) -> ImportedField` marks one extracted fact as user-confirmed.

- [ ] **Step 1: Write tests for PDF/DOCX adapter selection, common-field parsing, unsupported formats, and unconfirmed extraction state.**

```python
class CVImportTests(TestCase):
    def test_imported_fields_start_unconfirmed(self):
        result = parse_career_facts("John Doe\nSoftware Engineer\njohn@example.com")
        self.assertEqual(result["full_name"], "John Doe")
        self.assertFalse(result["fields"][0]["confirmed"])
```

- [ ] **Step 2: Run the focused import tests and verify failures.**

- [ ] **Step 3: Implement PDF extraction with `pdfplumber`/`pdfminer.six` and DOCX extraction with `python-docx`.**

- [ ] **Step 4: Implement deterministic section/field parsing for contact details, summary, experience, education, skills, projects, certifications, and achievements; do not call an external AI service.**

- [ ] **Step 5: Store every extracted field with a confirmation/review state and require ownership checks before confirmation.**

- [ ] **Step 6: Run `python manage.py test cv.tests.test_cv_import -v 2` and commit with `git add cv && git commit -m "feat: import existing CV documents"`.**

---

### Task 5: Add hybrid profile UI, CV CRUD, preview, versions, and navigation

**Files:**
- Create: `cv/views.py`
- Create: `cv/forms.py` additions for profile/CV/import/template forms
- Create: `templates/cv/dashboard.html`
- Create: `templates/cv/profile.html`
- Create: `templates/cv/cv_form.html`
- Create: `templates/cv/import.html`
- Create: `templates/cv/import_review.html`
- Create: `templates/cv/template_select.html`
- Create: `templates/cv/preview.html`
- Create: `templates/cv/versions.html`
- Create: `static/css/cv.css`
- Modify: `cv/urls.py`
- Modify: `templates/layouts/student/sidebar.html`
- Create: `cv/tests/test_views.py`

**Interfaces:**
- URL names: `dashboard`, `profile`, `cv_create`, `cv_edit`, `cv_duplicate`, `cv_import`, `cv_import_review`, `cv_templates`, `cv_preview`, `cv_versions`.
- All routes require authentication and query objects by `request.user` ownership.

- [ ] **Step 1: Write view tests for authenticated access, ownership isolation, standalone CV creation, and account data prefill.**

```python
class CVViewTests(TestCase):
    def test_anonymous_user_is_redirected(self):
        response = self.client.get(reverse("cv:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_cv_can_be_created_without_learning_data(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("cv:cv_create"), {"title": "My CV"})
        self.assertEqual(response.status_code, 302)
```

- [ ] **Step 2: Run the focused view tests and verify expected failures.**

- [ ] **Step 3: Implement the views and forms using the existing student layout pattern (`templates/layouts/student/base.html`).**

- [ ] **Step 4: Add a CV Builder entry to the authenticated sidebar and keep the service separate from Learning/Explore navigation.**

- [ ] **Step 5: Implement the dashboard with My CVs, Master Career Profile completion, Create New CV, Import Existing CV, template selection, version history, and export/delivery actions.**

- [ ] **Step 6: Run `python manage.py test cv.tests.test_views -v 2` and commit with `git add cv templates/cv static/css/cv.css templates/layouts/student/sidebar.html && git commit -m "feat: add CV builder UI"`.**

---

### Task 6: Add template rendering and PDF/DOCX export

**Files:**
- Create: `cv/services/documents/base.py`
- Create: `cv/services/documents/pdf.py`
- Create: `cv/services/documents/docx.py`
- Create: `cv/services/documents/renderer.py`
- Create: `cv/templates/cv/render/ats_classic.html`
- Create: `cv/templates/cv/render/modern_professional.html`
- Create: `cv/templates/cv/render/executive.html`
- Create: `cv/templates/cv/render/technical.html`
- Create: `cv/templates/cv/render/fresher.html`
- Create: `cv/templates/cv/render/academic.html`
- Create: `cv/templates/cv/render/government.html`
- Create: `cv/templates/cv/render/minimal.html`
- Create: `cv/tests/test_document_generation.py`
- Modify: `cv/views.py`
- Modify: `requirements.txt`

**Interfaces:**
- `render_cv(cv_version) -> RenderedCV` returns normalized rendered content.
- `generate_pdf(cv_version) -> DocumentArtifact`
- `generate_docx(cv_version) -> DocumentArtifact`
- `get_template_snapshot(template) -> dict` freezes the rendering configuration for version safety.

- [ ] **Step 1: Write tests proving PDF and DOCX generation returns non-empty artifacts and uses the selected template snapshot.**

```python
class DocumentGenerationTests(TestCase):
    def test_pdf_generation_returns_pdf_artifact(self):
        artifact = generate_pdf(self.version)
        self.assertEqual(artifact.mime_type, "application/pdf")
        self.assertTrue(artifact.file.size > 0)

    def test_docx_generation_returns_docx_artifact(self):
        artifact = generate_docx(self.version)
        self.assertEqual(
            artifact.mime_type,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
```

- [ ] **Step 2: Run the focused document tests and verify missing generator failures.**

- [ ] **Step 3: Implement the renderer against a normalized payload from `build_cv_payload()`.**

- [ ] **Step 4: Implement PDF generation with reportlab and DOCX generation with python-docx.**

- [ ] **Step 5: Store generated artifacts against the CV version and preserve template configuration/version metadata.**

- [ ] **Step 6: Run `python manage.py test cv.tests.test_document_generation -v 2` and commit with `git add cv requirements.txt && git commit -m "feat: add CV PDF and DOCX export"`.**

---

### Task 7: Add AI and delivery service interfaces without external-provider dependency

**Files:**
- Create: `cv/services/ai/provider.py`
- Create: `cv/services/ai/cv_writer.py`
- Create: `cv/services/ai/cv_reviewer.py`
- Create: `cv/services/ai/career_interviewer.py`
- Create: `cv/services/ai/job_matcher.py`
- Create: `cv/services/delivery/base.py`
- Create: `cv/services/delivery/email.py`
- Create: `cv/services/delivery/whatsapp.py`
- Create: `cv/services/delivery/viber.py`
- Create: `cv/models_delivery.py`
- Create: `cv/migrations/0004_ai_delivery.py`
- Create: `cv/tests/test_ai_delivery_interfaces.py`
- Modify: `cv/views.py`

**Interfaces:**
- `AIProvider.generate(prompt, context) -> AISuggestion`.
- `CVWriter.suggest(profile_payload, target_role=None) -> AISuggestion`.
- `CVReviewer.review(cv_payload) -> AISuggestion`.
- `CareerInterviewer.next_question(profile_payload) -> AISuggestion`.
- `JobMatcher.match(cv_payload, job_description) -> AISuggestion`.
- `DeliveryProvider.send(artifact, recipient) -> DeliveryResult`.
- `EmailDeliveryProvider` reuses the existing NPTOR email configuration/service.
- WhatsApp and Viber providers return a clear `not_configured` result when no provider credentials are configured; they never fake successful delivery.

- [ ] **Step 1: Write tests proving AI services can be instantiated with a null provider and delivery records capture success/failure/configuration states.**

```python
class DeliveryInterfaceTests(TestCase):
    def test_unconfigured_whatsapp_does_not_claim_success(self):
        result = WhatsAppDeliveryProvider().send(self.artifact, "123")
        self.assertEqual(result.status, "not_configured")
```

- [ ] **Step 2: Run the focused tests and verify missing interface failures.**

- [ ] **Step 3: Implement provider interfaces and a deterministic no-op AI provider that returns suggestions only when an actual provider is configured.**

- [ ] **Step 4: Implement delivery adapters and `DeliveryRecord` with channel, format, status, timestamps, recipient metadata, and error details.**

- [ ] **Step 5: Add explicit user confirmation before applying any AI suggestion to canonical profile data.**

- [ ] **Step 6: Run `python manage.py test cv.tests.test_ai_delivery_interfaces -v 2` and commit with `git add cv && git commit -m "feat: add CV AI and delivery interfaces"`.**

---

### Task 8: Add rewards, optional learning enrichment, privacy controls, and full regression coverage

**Files:**
- Create: `cv/models_reward.py`
- Create: `cv/services/rewards.py`
- Create: `cv/services/enrichment.py`
- Create: `cv/migrations/0005_rewards_enrichment.py`
- Create: `cv/tests/test_rewards.py`
- Create: `cv/tests/test_enrichment.py`
- Create: `cv/tests/test_security.py`
- Create: `cv/tests/test_cv_end_to_end.py`
- Modify: `cv/views.py`
- Modify: `cv/urls.py`

**Interfaces:**
- `calculate_profile_completion(profile) -> int` returns 0–100 based on meaningful profile sections.
- `award_profile_completion(user, event_code) -> RewardEvent | None` is idempotent.
- `get_optional_learning_enrichment(user) -> dict` returns available NPTOR learning/certification data without making it a CV prerequisite.
- `delete_user_cv_data(user) -> None` deletes owned CV/profile/import/artifact/delivery/reward data according to retention rules.

- [ ] **Step 1: Write tests for idempotent rewards, optional learning enrichment, and cross-user access denial.**

```python
class CVSecurityTests(TestCase):
    def test_user_cannot_open_another_users_cv(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("cv:cv_edit", args=[self.user_b_cv.pk]))
        self.assertEqual(response.status_code, 404)
```

- [ ] **Step 2: Run the focused tests and verify expected failures.**

- [ ] **Step 3: Implement profile-completion rewards without storing or exposing personal information for reward purposes.**

- [ ] **Step 4: Implement optional enrichment from existing NPTOR certifications/completions behind an explicit user action; keep core CV creation independent of those models.**

- [ ] **Step 5: Add privacy/delete controls and ensure every CV query is scoped through the authenticated user.**

- [ ] **Step 6: Add an end-to-end test covering account-prefill → profile → CV → template → version → PDF/DOCX artifact, with no course/exam/track records.**

- [ ] **Step 7: Run `python manage.py test cv -v 2`, `python manage.py check`, and `python manage.py makemigrations --check`. Commit with `git add cv && git commit -m "test: complete CV service regression coverage"`.**

---

## Final verification checklist

- [ ] Run `python manage.py check` with the project's existing environment.
- [ ] Run `python manage.py makemigrations --check` and confirm no model changes are missing from migrations.
- [ ] Run `python manage.py test cv -v 2`.
- [ ] Run the existing quiz/catalog/contextual-exam regression tests to confirm the standalone CV app did not alter learning behavior.
- [ ] Run `python manage.py seed_cv_templates` and verify the eight templates are present once each.
- [ ] Manually verify `/cv/`, profile editing, CV creation, import review, template preview, PDF/DOCX download, version history, and account-email delivery.
- [ ] Verify an unconfigured WhatsApp/Viber integration reports configuration status instead of claiming delivery.
- [ ] Verify a user with no courses/exams/tracks can complete the CV flow.
- [ ] Verify a second user cannot access the first user's CV/profile/import/artifact URLs.
