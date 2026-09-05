# Track Detail and Locking

## Goal
Provide a certification-oriented track page with deterministic exam progression while preserving the existing access service and exam flow.

## Progression
- Published public track exams are ordered by `created_at`, then `id`.
- The first exam is unlocked.
- Each later exam requires the immediately previous exam to have a submitted, passing attempt.
- Existing explicit `Exam.prerequisite_exams` remain enforced in addition to track ordering.
- A passing score is the existing exam `passing_score`; no new score threshold model is introduced.

## Access
- `AccessService` remains the source of entitlement decisions.
- Track progression is enforced by `can_access_exam()` so direct exam access and track subscriptions cannot bypass progression locks.
- Free exams remain free, but they are still subject to progression/prerequisite rules.
- Paid exams without access remain previewable; paid track access does not bypass progression locks.

## UI
- Show overall completion percentage and completed/total exams.
- Show each exam's number, metrics, pass score, completion state, and lock reason.
- Use Start for an accessible unlocked exam, Preview for an inaccessible paid exam, and Locked for an exam blocked by progression.
- Keep checkout and exam URLs unchanged.

## Schema decision
The current schema has no explicit track-exam ordering field. This phase therefore uses deterministic creation order instead of adding a migration. An explicit ordering field can be introduced later if administrators need manual reordering.
