# Government Exam Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a student-facing Government Exams catalog from country through exam program and connect each program to reusable NPTOR courses and exams.

**Architecture:** Keep the new government catalog as metadata above the existing quiz/course engines. Use Country → GovernmentBody → GovernmentJob → GovernmentExamProgram → GovernmentExamVersion → GovernmentExamStage, with `GovernmentExamProgram.courses` mapping to reusable courses and stages mapping to reusable exams.

**Tech Stack:** Django 6, MySQL, existing NPTOR templates/CSS, Django TestCase, GitHub main branch.

**Spec:** `docs/superpowers/specs/2026-09-05-government-exam-catalog-design.md`

## Global Constraints

- Do not create a second exam or course engine.
- Show only active catalog records and published student-facing resources.
- Preserve existing access controls for courses and exams.
- Keep country differences data-driven.
- Do not overwrite historical exam versions.

---

### Task 1: Map preparation courses to government exam programs

**Files:**
- Modify: `quiz/models/government_exam_program.py`
- Create: `quiz/migrations/0005_government_exam_program_courses.py` after the remote `quiz.0004` alignment migration exists

**Interfaces:**
- Produces: `GovernmentExamProgram.courses`, a blank many-to-many relationship to `courses.Course` with related name `government_exam_programs`.

- [ ] Add the many-to-many field to the program model.
- [ ] Generate the migration locally after `quiz.0004_align_current_quiz_models` is committed.
- [ ] Run `python manage.py migrate quiz`.
- [ ] Run `python manage.py makemigrations --check` and require no model changes.

### Task 2: Add student catalog views and routes

**Files:**
- Create: `quiz/views/government_catalog.py`
- Modify: `quiz/urls/urls.py`

**Interfaces:**
- Produces: `government_catalog`, `government_country`, `government_body`, and `government_program` views.
- Routes: `/government-exams/`, `/government-exams/<country_slug>/`, `/government-exams/<country_slug>/<body_slug>/`, `/government-exams/<country_slug>/<body_slug>/<program_slug>/`.

- [ ] Query only active countries/bodies/jobs/programs.
- [ ] On the country page, show body counts and active programs.
- [ ] On the body page, show active jobs and programs.
- [ ] On the program page, show active versions, stages, published exams, and published/public courses mapped to the program.
- [ ] Use existing exam detail and course learning URLs for actions.
- [ ] Preserve official website/syllabus/notification URLs when present.

### Task 3: Build student-facing templates and navigation

**Files:**
- Create: `templates/quiz/student/government_catalog.html`
- Create: `templates/quiz/student/government_country.html`
- Create: `templates/quiz/student/government_body.html`
- Create: `templates/quiz/student/government_program.html`
- Create: `static/css/pages/government_catalog.css`
- Modify: `templates/layouts/student/sidebar.html`
- Modify: `templates/quiz/student/learning_marketplace.html`

**Interfaces:**
- Consumes: catalog view context from Task 2.
- Produces: visible Government Exams entry point and responsive country/body/program pages.

- [ ] Add a Government Exams entry to the Learning Path sidebar.
- [ ] Add a Government Exams section/card to the marketplace without breaking existing certification discovery.
- [ ] Build clear breadcrumbs and back navigation.
- [ ] Show country cards, body cards, job chips, program cards, exam cards, and course cards.
- [ ] Add mobile-responsive layout and empty states.

### Task 4: Improve admin mapping controls

**Files:**
- Modify: `quiz/admin_government_catalog.py`

**Interfaces:**
- Produces: searchable/filterable course mapping in GovernmentExamProgram admin.

- [ ] Add `courses` to `filter_horizontal` for program admin.
- [ ] Add course search/list filters where supported without disrupting existing job mapping.

### Task 5: Seed initial government catalog metadata

**Files:**
- Create: `quiz/management/commands/seed_government_catalog.py`

**Interfaces:**
- Produces: idempotent catalog metadata for Nepal, India, and USA, with initial government bodies/jobs/programs.

- [ ] Create/reuse the Government / Competitive Exam content vertical.
- [ ] Upsert countries by code.
- [ ] Upsert initial bodies and jobs using stable codes/slugs.
- [ ] Upsert initial exam programs and link their jobs.
- [ ] Do not fabricate detailed exam patterns or eligibility requirements; leave those to verified content later.
- [ ] Make the command safe to run repeatedly.

### Task 6: Add regression tests

**Files:**
- Create: `quiz/tests/test_government_catalog.py`

**Interfaces:**
- Produces coverage for catalog hierarchy, filtering, URL resolution, and resource visibility.

- [ ] Test inactive countries/bodies/programs are excluded.
- [ ] Test program page returns only published/public mapped courses.
- [ ] Test program page returns only published exams through active stages.
- [ ] Test country/body/program slug traversal resolves the correct hierarchy.
- [ ] Test empty catalog sections render without exceptions.

### Task 7: Verification and commits

**Files:**
- All files from Tasks 1–6.

- [ ] Run `python manage.py migrate`.
- [ ] Run `python manage.py makemigrations --check`.
- [ ] Run focused catalog tests.
- [ ] Run the broader quiz test suite if available and practical.
- [ ] Run `python manage.py check`.
- [ ] Inspect `git diff` and `git status`.
- [ ] Commit model/migration work together and commit UI/catalog work with tests together, or squash them into one feature commit on `main`.
