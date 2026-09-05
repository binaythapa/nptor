# Vertical Catalog And Contextual Exams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate student catalogs by content vertical and ensure exams can only be launched through an authorized course lesson or certification track.

**Architecture:** Add an explicit nullable `ContentVertical` relationship to `Domain` so catalog filtering is data-driven instead of based on names. The marketplace accepts a vertical context and exposes only courses/tracks; exam records remain internal to course lessons and track sequences. Exam launch validates either a course lesson context or a track membership/context before creating an attempt.

**Tech Stack:** Django 6, MySQL, Django ORM, Django test client, existing NPTOR Course/Lesson/Exam/ExamTrack models.

**Spec:** User-approved design in conversation: `/quiz/certifications/` shows only certification content; `/quiz/academic-entrance/` shows only academic/entrance content; exams are accessible only through courses and tracks.

## Global Constraints

- Do not merge Course, Exam, and ExamTrack into one model.
- Keep reusable Exam records internally reusable by courses and tracks.
- Do not expose standalone exams as marketplace resources.
- Direct exam start/detail/preview URLs must not create or expose an exam attempt without valid course/track context.
- Preserve existing course quiz max-attempt and prerequisite checks.
- Preserve existing track prerequisite/access behavior.
- Add migrations for schema changes and keep MySQL compatibility.

---

### Task 1: Add explicit domain vertical classification

**Files:**
- Modify: `quiz/models/category.py`
- Create: `quiz/migrations/0007_domain_content_vertical.py`

- [ ] **Step 1: Add `content_vertical` nullable foreign key to Domain.**

```python
content_vertical = models.ForeignKey(
    "quiz.ContentVertical",
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name="domains",
)
```

- [ ] **Step 2: Add a migration after `0006_preparationprogram`.**
- [ ] **Step 3: In the migration, classify existing domains by known seeded slugs: `mbbs-entrance`, `ioe-entrance`, `class-11-entrance`, and `mba-entrance` as academic; government catalog domains as government; remaining public domains as professional certification. Leave organization-owned domains untouched.
- [ ] **Step 4: Commit the schema/data classification change.**

```bash
git add quiz/models/category.py quiz/migrations/0007_domain_content_vertical.py
git commit -m "feat: classify learning domains by content vertical"
```

### Task 2: Add vertical filtering to the learning marketplace

**Files:**
- Modify: `quiz/services/learning_catalog.py`
- Modify: `quiz/views/learning_marketplace.py`
- Modify: `quiz/urls/urls.py`
- Modify: `templates/quiz/student/learning_marketplace.html`
- Test: `quiz/tests/test_learning_catalog_verticals.py`

- [ ] **Step 1: Write tests proving academic and certification catalogs do not leak each other.**
- [ ] **Step 2: Run the focused tests and verify they fail before implementation.**
- [ ] **Step 3: Add `catalog_vertical` to `build_learning_catalog()` and filter courses, tracks, and internal exam/domain summaries by `Domain.content_vertical`.
- [ ] **Step 4: Add `catalog_vertical` request handling and meaningful labels in `learning_marketplace`.
- [ ] **Step 5: Keep exams available only for internal track/course relationships; remove the Exams marketplace tab and standalone exam resource rows.
- [ ] **Step 6: Point `/quiz/certifications/` and `/quiz/academic-entrance/` at the filtered marketplace contexts.
- [ ] **Step 7: Update the marketplace heading/copy to identify the selected vertical.
- [ ] **Step 8: Run focused catalog tests and verify they pass.
- [ ] **Step 9: Commit.**

```bash
git add quiz/services/learning_catalog.py quiz/views/learning_marketplace.py quiz/urls/urls.py templates/quiz/student/learning_marketplace.html quiz/tests/test_learning_catalog_verticals.py
git commit -m "feat: separate certification and academic catalogs"
```

### Task 3: Require contextual exam launches

**Files:**
- Modify: `quiz/views/course_exam_start.py`
- Modify: `quiz/views/exams.py`
- Modify: `quiz/views/learning_track.py`
- Modify: `templates/quiz/student/learning_track.html`
- Modify: `quiz/views/exam_detail.py`
- Modify: `quiz/views/exam_preview.py`
- Test: `quiz/tests/test_contextual_exam_access.py`

- [ ] **Step 1: Write tests proving a direct exam start is denied, a valid course lesson start works, and a valid track start works.
- [ ] **Step 2: Run the focused tests and verify the direct-start case fails before implementation.
- [ ] **Step 3: Make `course_exam_start` reject missing course/lesson context instead of delegating to the standalone launcher.
- [ ] **Step 4: Add validated `track` context to the standard exam launcher: confirm the exam belongs to the requested active track, confirm track access, and store track context in the session.
- [ ] **Step 5: Update the track template to pass its track slug when launching an exam.
- [ ] **Step 6: Prevent standalone exam detail/preview pages from exposing an exam as a student entry point; redirect to the appropriate parent/catalog when no valid context exists.
- [ ] **Step 7: Preserve prerequisite and max-attempt behavior.
- [ ] **Step 8: Run focused exam access tests and verify they pass.
- [ ] **Step 9: Commit.**

```bash
git add quiz/views/course_exam_start.py quiz/views/exams.py quiz/views/learning_track.py templates/quiz/student/learning_track.html quiz/views/exam_detail.py quiz/views/exam_preview.py quiz/tests/test_contextual_exam_access.py
git commit -m "feat: restrict exams to course and track entry points"
```

### Task 4: Final regression verification

- [ ] **Step 1: Run the full relevant quiz test set.**

```bash
python manage.py test quiz.tests.test_learning_catalog_verticals quiz.tests.test_contextual_exam_access quiz.tests.test_student_sidebar quiz.tests.test_student_navigation_destinations
```

- [ ] **Step 2: Run Django system checks.**

```bash
python manage.py check
```

- [ ] **Step 3: Verify the migration plan.**

```bash
python manage.py showmigrations quiz
```

- [ ] **Step 4: Review the final diff and confirm only the intended catalog/exam-access files changed.**
- [ ] **Step 5: Commit any final test-only corrections if needed.
