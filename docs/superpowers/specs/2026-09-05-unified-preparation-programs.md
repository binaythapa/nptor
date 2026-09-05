# Unified Preparation Program Design

## Goal

Give NPTOR one reusable catalog layer for professional certifications, government exams, entrance exams, and academic preparation without creating separate Course models for MBBS, IOE, Class 11, or future exam families.

## Architecture

NPTOR keeps three concerns separate:

1. **Catalog / preparation context** — `PreparationProgram` identifies what a learner is preparing for.
2. **Learning** — the existing `Course -> CourseSection -> Lesson -> Progress` system owns instructional content.
3. **Assessment** — the existing `Exam`, question-bank, allocation, and attempt system owns testing.

`ContentVertical` remains the top-level taxonomy. `PreparationProgram` is a reusable grouping layer that can be used for academic/entrance/custom preparation immediately and can later become the unified presentation layer for specialized government/professional catalogs.

## Program examples

- `ACADEMIC_EXAM`: Class 11 Entrance Preparation, Class 12 Board Preparation.
- `ACADEMIC_EXAM`: MBBS Entrance Preparation.
- `ACADEMIC_EXAM`: IOE Entrance Preparation.
- `PROFESSIONAL_CERTIFICATION`: a future preparation bundle around a certification.
- `GOVERNMENT_EXAM`: a future generic presentation layer for an existing `GovernmentExamProgram`.

The implementation does **not** replace the existing `GovernmentExamProgram` hierarchy. Government-specific body/job/version/stage data remains intact and can be unified later without duplicating that domain logic.

## PreparationProgram fields

- `content_vertical` — required FK to `ContentVertical`.
- `country` — optional FK to `Country`; useful for Nepal/India/local catalogs without forcing geography onto global certifications.
- `name`, `code`, `slug`, `description` — stable catalog identity and presentation.
- `official_website` — optional reference link.
- `courses` — M2M to reusable `Course` records.
- `exams` — M2M to reusable `Exam` records.
- `is_active` — catalog availability flag.
- `is_published` — learner-facing publication flag.
- `created_at`, `updated_at` — audit timestamps.

Uniqueness is `(content_vertical, code)` so the same code can exist in different verticals while avoiding duplicate programs inside one vertical.

## Management rules

- Admins create a `ContentVertical` first, then a `PreparationProgram`.
- Courses and exams are attached to a program; their existing pricing/access models remain authoritative.
- A course is never duplicated just because it belongs to another program.
- A program may contain multiple courses and exams.
- A course or exam may be reused by multiple programs where the content genuinely overlaps.
- Country is optional because professional certifications can be global.
- Publication is separate from activity so admins can prepare a catalog before exposing it to learners.

## Learner experience

The next UI phase should present programs uniformly as:

`Program -> Learn -> Practice -> Mock Exams -> Performance -> Study Plan`

Vertical-specific details remain extensions. For example, government programs can additionally expose job/post, stage, and exam-update information.

## Seed scope

This phase seeds three non-government examples only as catalog records:

- Nepal / Academic Exam / MBBS Entrance Preparation
- Nepal / Academic Exam / IOE Entrance Preparation
- Nepal / Academic Exam / Class 11 Entrance Preparation

No copyrighted course/question content is copied into the repository. These records are scaffolding for attaching original NPTOR courses and exams through admin.

## Out of scope

- Replacing `GovernmentExamProgram`.
- Migrating existing government records.
- Creating a new question taxonomy.
- Changing Course or Exam pricing/access behavior.
- Building the full learner-facing program dashboard.
- Importing official exam papers or copyrighted coaching material.
