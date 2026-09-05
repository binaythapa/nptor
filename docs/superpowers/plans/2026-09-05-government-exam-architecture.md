# Government Exam Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a scalable, versioned government-exam catalog layer that reuses NPTOR's existing assessment and learning engines.

**Architecture:** Add normalized catalog models for content vertical, country, government body, job/post, exam program, version, and stage. Keep the existing `Exam` as the assessment engine and connect versioned stages to it; keep questions/courses/progress/subscriptions unchanged.

**Tech Stack:** Django ORM, MySQL-compatible relational database, existing NPTOR quiz models/admin/tests.

**Spec:** `docs/superpowers/specs/2026-09-05-government-exam-architecture-design.md`

## Global Constraints

- Reuse the existing `Exam`, `Question`, `Course`, `TrackExam`, and `UserExam` engines.
- Do not introduce country-specific branching into core services.
- Government catalog records may be global (`organization = NULL`).
- Use normalized foreign-key relationships for high-cardinality catalog data.
- Preserve version/history rather than mutating historical assessment definitions.
- Keep frequently filtered catalog/status/order fields indexed.
- Do not copy copyrighted question banks.

---

### Task 1: Add catalog model primitives

**Files:**
- Create: `quiz/models/content_vertical.py`
- Create: `quiz/models/country.py`
- Create: `quiz/models/government_body.py`
- Create: `quiz/models/government_job.py`
- Create: `quiz/models/government_exam_program.py`
- Create: `quiz/models/government_exam_version.py`
- Create: `quiz/models/government_exam_stage.py`
- Modify: `quiz/models/__init__.py`

**Interfaces:**
- Catalog models expose stable IDs/slugs/codes, status, timestamps, and normalized foreign keys.
- `GovernmentExamStage.exam` points to the existing reusable `Exam`.
- `GovernmentExamVersion.program` points to `GovernmentExamProgram`.

- [ ] Add the models and constraints/indexes.
- [ ] Export them from `quiz.models`.

### Task 2: Add migration

**Files:**
- Create: `quiz/migrations/<new_catalog_migration>.py`

- [ ] Generate/write the migration matching the new models.
- [ ] Verify migration dependencies target the current migration graph.

### Task 3: Add admin management

**Files:**
- Modify: `quiz/admin.py`

- [ ] Register catalog models with useful list/search/filter fields.
- [ ] Make version/stage management practical for content administrators.

### Task 4: Add regression tests

**Files:**
- Create: `quiz/tests/test_government_exam_catalog.py`

- [ ] Test country → body → job → program → version → stage relationships.
- [ ] Test one version can have multiple ordered stages linked to reusable `Exam` records.
- [ ] Test uniqueness constraints and slug/code behavior.
- [ ] Test global catalog records can remain organization-independent.
- [ ] Test historical versions can coexist rather than overwrite one another.

### Task 5: Verify and commit

- [ ] Run Django checks/tests available in the environment.
- [ ] Run migration consistency checks.
- [ ] Review the final diff for accidental changes or country-specific coupling.
- [ ] Commit the implementation as a focused change.
