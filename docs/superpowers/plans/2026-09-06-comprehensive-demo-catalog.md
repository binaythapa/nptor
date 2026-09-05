# Comprehensive Demo Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one idempotent NPTOR demo-data command that populates reusable domains, hierarchical categories, original questions, exams, exam tracks, preparation programs, courses, sections, and article/video/practice/quiz lessons across professional, academic/entrance, and government preparation.

**Architecture:** Reuse existing `Domain`, `Category`, `Question`, `Choice`, `Exam`, `ExamCategoryAllocation`, `ExamTrack`, `TrackExam`, `PreparationProgram`, `Course`, `CourseSection`, and `Lesson` models. Keep government-specific body/job/version/stage records in the existing government catalog command, while this command adds the learner-facing preparation/course/assessment data and links it to those records. Make all writes deterministic and idempotent so the complete flow can be rebuilt repeatedly in a development database.

**Tech Stack:** Django management commands, Django ORM, MySQL-compatible data, existing NPTOR quiz/course models.

**Spec:** `docs/superpowers/specs/2026-09-05-unified-preparation-programs.md`

## Global Constraints

- Reuse existing models; do not create subject-specific Course or Exam models.
- Seed original educational content only; do not copy copyrighted books, paid coaching banks, or complete official papers.
- Keep government body/job/version/stage semantics in the existing government catalog.
- Keep pricing/access on Course, Exam, ExamTrack, and subscription plans rather than duplicating pricing in PreparationProgram.
- All seed commands must be safe to run repeatedly without multiplying records.
- The dataset must exercise text, video, practice, and quiz lesson types.
- The dataset must exercise all currently supported question types with valid grading data.

---

### Task 1: Add focused tests for the complete catalog contract

**Files:**
- Create: `quiz/tests/test_complete_catalog_seed.py`

**Interfaces:**
- Consumes: `seed_complete_catalog` management command.
- Produces: assertions for deterministic counts, representative relationships, lesson types, question types, and idempotency.

- [ ] **Step 1: Write tests for command creation and representative catalog objects.**
- [ ] **Step 2: Assert the command creates professional, academic/entrance, and government-linked preparation records.**
- [ ] **Step 3: Assert every representative course has article, video, practice, and quiz lessons.**
- [ ] **Step 4: Assert every supported Question type has at least one original seed question and valid answer payload.**
- [ ] **Step 5: Assert exams have allocations and tracks have TrackExam relationships.**
- [ ] **Step 6: Assert running the command twice leaves counts unchanged.**

### Task 2: Implement reusable seed helpers and core taxonomy

**Files:**
- Create: `quiz/management/commands/seed_complete_catalog.py`

**Interfaces:**
- Consumes: existing model APIs.
- Produces: `Command.handle()` and private deterministic helpers for domains, categories, questions, exams, tracks, preparation programs, and courses.

- [ ] **Step 1: Add constants for vertical/program slugs and original question payloads.**
- [ ] **Step 2: Add `get_or_create`/`update_or_create` helpers for domains and hierarchical categories.**
- [ ] **Step 3: Add a question helper that creates/updates `Question` and its `Choice` rows, including multi-select and structured answer fields.**
- [ ] **Step 4: Add question fixtures covering single, multi, true/false, dropdown, fill, numeric, matching, and ordering.**
- [ ] **Step 5: Attach primary and additional categories deterministically.**

### Task 3: Seed exams, allocations, and tracks

**Files:**
- Modify: `quiz/management/commands/seed_complete_catalog.py`

**Interfaces:**
- Consumes: categories and questions from Task 2.
- Produces: reusable `Exam`, `ExamCategoryAllocation`, `ExamTrack`, and `TrackExam` records.

- [ ] **Step 1: Create representative exams for SnowPro, MBA, MBBS, IOE, Class 11, and government preparation.**
- [ ] **Step 2: Create deterministic category allocations whose percentages total 100 for each exam.**
- [ ] **Step 3: Create one or more tracks per preparation family and attach reusable exams in explicit order.**
- [ ] **Step 4: Configure published mock exams with realistic durations, passing scores, review settings, and mock-attempt limits.**

### Task 4: Seed preparation programs and reusable courses

**Files:**
- Modify: `quiz/management/commands/seed_complete_catalog.py`

**Interfaces:**
- Consumes: existing preparation-program and government-program records.
- Produces: preparation programs linked to reusable courses and exams.

- [ ] **Step 1: Ensure academic preparation programs exist for MBBS, IOE, Class 11, and MBA.**
- [ ] **Step 2: Link professional certification preparation to reusable certification courses/exams without duplicating government-specific entities.**
- [ ] **Step 3: Link government preparation programs to their reusable courses and exams using existing `GovernmentExamProgram` records.**
- [ ] **Step 4: Make every seeded course platform-owned, approved, published, and public for development-flow testing.**

### Task 5: Seed complete course lesson content

**Files:**
- Modify: `quiz/management/commands/seed_complete_catalog.py`

**Interfaces:**
- Consumes: courses, exams, domains, and categories.
- Produces: ordered `CourseSection` and `Lesson` records exercising all lesson types.

- [ ] **Step 1: Create at least two sections for each representative course.**
- [ ] **Step 2: Add original article lessons with concise educational HTML.**
- [ ] **Step 3: Add video lessons using stable safe demo/public video URLs and no copyrighted course uploads.**
- [ ] **Step 4: Add practice lessons configured with a domain, category, difficulty, threshold, and accuracy settings.**
- [ ] **Step 5: Add quiz lessons linked to reusable exams with explicit completion settings.**
- [ ] **Step 6: Ensure reruns update content without creating duplicate sections or lessons.**

### Task 6: Integrate with the unified seed command and verify

**Files:**
- Modify: `quiz/management/commands/seed_nptor_catalog.py`
- Modify: `quiz/tests/test_complete_catalog_seed.py`

- [ ] **Step 1: Run the government and preparation seed commands before the complete learner catalog seed.**
- [ ] **Step 2: Add the complete catalog command to `seed_nptor_catalog` after prerequisite catalog commands.**
- [ ] **Step 3: Run focused seed tests.**
- [ ] **Step 4: Run `python manage.py check`.**
- [ ] **Step 5: Run existing government catalog, student navigation, preparation-program, and course tests to detect regressions.**
- [ ] **Step 6: Run the complete seed command twice and confirm idempotency.**
- [ ] **Step 7: Review the diff for accidental production behavior changes and commit the implementation.**
