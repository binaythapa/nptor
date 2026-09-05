# Independent Exams and Track Composition

## Goal
Make exams reusable, non-commercial assessment assets. Courses and tracks are the only student-facing purchasable resources.

## Model
- `Exam` is independent of `ExamTrack` and stores assessment/content configuration only.
- `TrackExam` joins a track to an exam with an explicit `position`/ordering field.
- `TrackExam` stores track-specific prerequisite relationships to other `TrackExam` rows.
- The same exam may appear in multiple tracks, with different order and prerequisites.
- Position does not implicitly create a prerequisite.
- Exam pricing fields and exam-level prerequisites are removed.
- Track pricing remains on track subscription plans; course pricing remains on course subscription plans.

## Access and progression
Track ownership grants access to exams included in that track. Starting an exam additionally requires all explicitly configured TrackExam prerequisites to be passed. Direct exam entitlements are retained only where required by existing generic access infrastructure, but the product flow no longer sells exams.

## Commerce
- Marketplace exposes courses and tracks as commercial products.
- Exam checkout is removed from the application flow.
- Existing payment-order exam support may be removed because existing data may be discarded.
- Track checkout prices only the selected active track plan.
- Course checkout prices only the selected active course plan.

## Admin
Admins create exams independently. Track administration attaches existing exams, orders them, and configures prerequisites from the exams already attached to that track.

## Data reset
Existing development data may be discarded. No compatibility/data migration is required; schema can be recreated cleanly.

## Testing
Cover model constraints, reusable exams, track-specific prerequisites, explicit-only locking, catalog visibility, access, and removal of exam commerce.
