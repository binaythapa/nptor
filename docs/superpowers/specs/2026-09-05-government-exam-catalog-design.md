# Government Exam Catalog Design

## Goal
Provide a student-facing Government Exams catalog that lets students browse by country, government body, job, and exam program, then reach the existing NPTOR courses, exams, practice, and mock flows.

## Architecture
The government catalog remains metadata above the existing learning engine: Country → GovernmentBody → GovernmentJob → GovernmentExamProgram → GovernmentExamVersion → GovernmentExamStage → existing Exam. Government exam preparation courses are mapped to programs so course discovery is scoped to the same preparation target.

## Student flow
1. Government Exams entry point from Learning.
2. Country catalog with active countries and counts.
3. Country page with government bodies.
4. Government body page with jobs and exam programs.
5. Program page with current version/stages, linked exams, and linked preparation courses.
6. Existing exam/course actions continue to use their existing URLs and access controls.

## Content rules
- Only active catalog records are shown.
- Only published public courses and published exams are shown to students.
- Official websites, syllabus URLs, and notification URLs are surfaced as external references when present.
- No country-specific application code; country differences are represented by catalog data.
- Historical exam versions remain separate from current versions.

## Data mapping
`GovernmentExamProgram.courses` is a many-to-many relationship to `courses.Course`. Exam stages already map versions to the reusable `quiz.Exam` model.

## Scope
This increment delivers the catalog navigation, student UI, course/exam mapping, admin usability, seed data for initial countries/bodies/jobs/programs, and regression tests. It does not replace the existing exam, course, practice, payment, or subscription engines.
