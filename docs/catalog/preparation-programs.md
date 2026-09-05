# Preparation Programs

`PreparationProgram` is the reusable catalog layer for exam-preparation products that do not need their own specialized catalog model.

## Admin workflow

1. Open **Content Vertical** in Django admin.
2. Create/verify the vertical, such as **Academic Exam**.
3. Open **Preparation Programs**.
4. Create the program and choose an optional country.
5. Attach existing **Courses** and **Exams** with the horizontal selectors.
6. Keep `is_published` off while building the catalog; enable it only when the program is ready for learners.

The program does not own pricing. Course and Exam subscription plans remain the source of truth for access.

## Examples

### MBBS

```text
Nepal / Academic Exam
└── MBBS Entrance Preparation
    ├── Biology Course
    ├── Chemistry Course
    ├── Physics Course
    └── MBBS Mock Exams
```

### IOE

```text
Nepal / Academic Exam
└── IOE Entrance Preparation
    ├── Mathematics Course
    ├── Physics Course
    ├── Chemistry Course
    └── IOE Mock Exams
```

### Class 11

```text
Nepal / Academic Exam
└── Class 11 Entrance Preparation
    ├── Stream/subject courses
    └── School or common entrance mock exams
```

These examples are catalog scaffolding only. Create original NPTOR learning content and questions rather than copying copyrighted books, paid coaching banks, or complete official papers.

## Reuse rule

A Course or Exam can be attached to multiple Preparation Programs when the same content genuinely applies. Do not clone a Course merely to place it in another catalog.

## Government exams

Government recruitment data remains managed by `GovernmentExamProgram`, `GovernmentExamVersion`, `GovernmentExamStage`, `GovernmentJob`, and `GovernmentBody`. This phase does not migrate those records. A later catalog-unification phase can use `PreparationProgram` as the common learner-facing layer while preserving those government-specific entities.
