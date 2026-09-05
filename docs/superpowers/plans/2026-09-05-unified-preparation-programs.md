# Unified Preparation Programs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable `PreparationProgram` catalog layer so NPTOR can manage MBBS, IOE, Class 11, and future preparation programs without creating specialized Course models.

**Architecture:** Add `PreparationProgram` to the quiz catalog. It references `ContentVertical`, optionally `Country`, and reusable `Course` and `Exam` records. Existing government-specific models remain unchanged and continue to own government body/job/version/stage semantics.

**Tech Stack:** Django ORM, MySQL-compatible migrations, Django admin, Django TestCase, existing quiz/course models.

**Spec:** `docs/superpowers/specs/2026-09-05-unified-preparation-programs.md`

## Global Constraints

- Reuse the existing `Course` and `Exam` models; do not create MBBSCourse/IOECourse/Class11Course models.
- Preserve the existing `GovernmentExamProgram` hierarchy and routes.
- Keep pricing/access behavior on `Course` and `Exam`; `PreparationProgram` only groups reusable products.
- Do not import copyrighted exam papers, books, or coaching-bank content.
- Use the existing `ContentVertical` taxonomy.

---

### Task 1: Add the preparation-program model and migration

**Files:**
- Create: `quiz/models/preparation_program.py`
- Modify: `quiz/models/__init__.py`
- Create: `quiz/migrations/0006_preparationprogram.py`
- Test: `quiz/tests/test_preparation_program_model.py`

**Interfaces:**
- Produces `PreparationProgram` with `content_vertical`, optional `country`, reusable `courses` and `exams`, publication/activity flags, and stable `(content_vertical, code)` uniqueness.

- [ ] **Step 1: Write failing model tests** for creation, uniqueness, optional country, and course/exam reuse.
- [ ] **Step 2: Run the focused test and verify it fails because the model does not exist.**
- [ ] **Step 3: Implement the model and export it from `quiz.models`.**
- [ ] **Step 4: Add the Django migration depending on `quiz 0005` and the current `courses` migration.**
- [ ] **Step 5: Re-run the focused tests and verify the model behavior.**

### Task 2: Add Django admin management

**Files:**
- Modify: `quiz/admin_government_catalog.py`
- Test: `quiz/tests/test_preparation_program_admin.py`

**Interfaces:**
- Produces a searchable/filterable admin registration for `PreparationProgram` with horizontal course/exam selection.

- [ ] **Step 1: Write a failing admin registration test.**
- [ ] **Step 2: Verify the focused test fails because the model is not registered/configured.**
- [ ] **Step 3: Register `PreparationProgram` with list display, filters, search, slug prepopulation, and horizontal course/exam widgets.**
- [ ] **Step 4: Re-run the focused admin test and verify it passes.**

### Task 3: Add non-government seed scaffolding

**Files:**
- Create: `quiz/management/commands/seed_preparation_programs.py`
- Test: `quiz/tests/test_preparation_program_seed.py`

**Interfaces:**
- Produces idempotent catalog records for MBBS Entrance Preparation, IOE Entrance Preparation, and Class 11 Entrance Preparation under Nepal and the Academic Exam vertical.

- [ ] **Step 1: Write failing seed-command tests that assert the three records exist after the command.**
- [ ] **Step 2: Verify the tests fail because the command does not exist.**
- [ ] **Step 3: Implement the idempotent seed command using `get_or_create`/`update_or_create` and existing Country/ContentVertical records.**
- [ ] **Step 4: Re-run the seed tests and verify repeat execution does not duplicate records.**

### Task 4: Document the catalog usage

**Files:**
- Create: `docs/catalog/preparation-programs.md`

- [ ] **Step 1: Document how an admin creates a program and attaches reusable courses/exams.**
- [ ] **Step 2: Include MBBS, IOE, and Class 11 examples.**
- [ ] **Step 3: Explain that government-specific records remain in `GovernmentExamProgram` until a later unification phase.**

### Task 5: Verify repository state

**Files:**
- No production files.

- [ ] **Step 1: Run `python manage.py test quiz.tests.test_preparation_program_model quiz.tests.test_preparation_program_admin quiz.tests.test_preparation_program_seed`.**
- [ ] **Step 2: Run `python manage.py check`.**
- [ ] **Step 3: Run the existing government catalog and student navigation tests to guard against regressions.**
- [ ] **Step 4: Review the final diff for accidental changes to government routes/models.**
- [ ] **Step 5: Commit with `feat: add unified preparation program catalog`.**
