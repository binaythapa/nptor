# NPTOR Government Exam Architecture Design

## Goal

Extend NPTOR so government and competitive exam content can scale across countries, recruiting bodies, jobs, exam programs, syllabus versions, stages, subjects, topics, and large reusable question banks without creating a separate exam engine or country-specific code paths.

## Design Principles

1. **Reuse the existing learning engine.** Government preparation uses the existing `Exam`, `Question`, `Course`, `TrackExam`, `UserExam`, progress, subscription, and practice infrastructure.
2. **Separate catalog metadata from learning content.** Country, recruiting body, job/post, exam program, syllabus version, and stages describe what an exam is; `Exam` describes how students take an assessment.
3. **Version first.** Syllabus/exam structures that change over time are represented by explicit versions so historical attempts remain tied to the correct definition.
4. **Reusable taxonomy.** Subjects and topics are normalized and reusable; questions can be associated with multiple categories rather than duplicated.
5. **Configuration over country-specific branching.** Country differences are represented as data and relationships wherever possible.
6. **Tenant-safe content.** Existing organization ownership remains the boundary for private/tenant content; global catalog records may be shared.
7. **Scale-aware queries.** Frequently filtered foreign keys/status fields receive indexes; large content collections are queried through narrow relations and paginated interfaces.

## Target Hierarchy

```text
Content Vertical
  -> Country
      -> Government / Recruiting Body
          -> Exam Program
              -> Exam Version
                  -> Job / Post (where applicable)
                  -> Exam Stage
                      -> Subject
                          -> Topic
                              -> reusable Question bank

Exam Program / Version / Stage
  -> existing Exam engine
  -> TrackExam / Course / Practice / Mock / UserExam
```

### Why this hierarchy

A country can have multiple recruiting bodies. A recruiting body can publish multiple exam programs. A program can change its syllabus or structure over time. A program can target one or many jobs/posts, and a recruitment process can have multiple stages. These relationships must not be encoded in a single `Exam` row or in country-specific Python logic.

## New Catalog Concepts

### ContentVertical
A small controlled taxonomy for top-level NPTOR products, initially including Professional Certification and Government/Competitive Exam. It should be data-driven rather than a boolean on `Exam`.

### Country
Canonical country metadata used for filtering and discovery. Use a stable code (ISO-style code) as the unique business identifier and keep display names separate.

### GovernmentBody
Represents a recruiting/exam authority such as a public service commission, staff selection commission, or another government recruiting organization. It belongs to a country.

### GovernmentJob
Represents a job/post/cadre that candidates may prepare for. It belongs to a recruiting body/country and can be associated with multiple exam programs or versions where the real-world structure requires it.

### GovernmentExamProgram
Represents the stable public-facing recruitment/examination program, independent of a particular year's syllabus. Examples include a civil service examination family or a public-service post examination.

### GovernmentExamVersion
Represents a dated/versioned definition of a program. It stores version label, effective dates/status, official syllabus/notification/source metadata, and links to the existing learning `Exam` records through stages. This prevents future syllabus updates from mutating historical preparation records.

### GovernmentExamStage
Represents a stage/paper/assessment within a version. It carries ordering, required/optional status, and the relationship to the existing `Exam` engine. Examples include prelims, mains, paper I, interview, or a competency assessment. Written-test stages use the current MCQ/exam engine; future non-MCQ stages can be represented as stages without forcing unsupported question types into the core engine.

### Subject / Topic
Use the existing category system as the immediate reusable taxonomy where possible. Do not create country-specific subject tables unless requirements prove the existing category model cannot represent the hierarchy. If a future taxonomy upgrade is needed, introduce explicit parent-child taxonomy carefully rather than duplicating categories.

## Existing Models Reused

- `Exam`: assessment configuration and access.
- `TrackExam`: sequencing/prerequisites within a learning track.
- `Question` and `Choice`: master reusable question bank.
- `Course`, `CourseSection`, `Lesson`: preparation content.
- `UserExam`: student attempts/history.
- Subscription/entitlement models: monetization/access.
- Existing organization fields: tenant isolation.

The current `Exam` intentionally has no hard-coded track relationship and supports categories, subscription plans, exam configuration, publishing, and review mode. The current `Question` supports primary and additional categories, multiple question types, difficulty, organization ownership, and soft deletion.

## Question Reuse Strategy

Questions remain independent content records. Exam stages select questions through the existing allocation/blueprint mechanism. A question can be used by multiple government exam versions and professional certifications when legitimately relevant. Do not clone a question merely because it appears in another exam catalog.

Questions should carry enough provenance metadata to distinguish NPTOR-created content from official source references. Official syllabus/notification URLs should be stored as source metadata, while copyrighted official question papers should not be copied wholesale into the platform.

## Versioning and Historical Integrity

A student attempt must point to the concrete `Exam` definition used at the time of the attempt. Government catalog versions may be updated or retired without modifying historical attempts. New syllabus versions should create new catalog/version relationships and, when the assessment definition materially changes, new `Exam` records. Existing attempts remain immutable historical records.

## Access and Multi-Tenancy

Government catalog records may be global (`organization = NULL`) and can optionally be offered by an organization. Student access continues through existing subscription/entitlement checks. Do not put pricing directly on government catalog entities.

## Scale Requirements

- Use integer foreign keys and normalized relations for high-cardinality entities.
- Add composite indexes for common discovery paths such as `(country, status)`, `(body, status)`, `(program, status)`, and `(version, order)` where supported by the final model design.
- Keep list views paginated and filter by indexed fields before joining large question tables.
- Avoid unbounded JSON for relationships that require filtering/reporting.
- Use slugs/codes for human-facing URLs, but use database IDs/foreign keys for relationships.
- Preserve soft deletion/status fields for catalog records rather than destructive deletion where history can exist.
- Keep source URLs and publication metadata separate from the core assessment records.

## Rollout Strategy

1. Add catalog primitives and migrations without changing the existing exam engine.
2. Add admin registration and validation.
3. Add tests for relationships, versioning, tenant/global behavior, and indexes/constraints.
4. Add Nepal catalog data first.
5. Add discovery/search UI and government exam dashboard.
6. Add India catalog.
7. Add additional countries only after validating the model against materially different recruitment systems.

## Explicit Non-Goals

- No separate GovernmentQuestion or GovernmentExam attempt engine.
- No country-specific branching throughout views/services.
- No bulk import of copyrighted question banks.
- No premature microservices or database sharding.
- No replacement of the existing `Category` model until real taxonomy requirements demonstrate a need.
