# Independent Exams and Track Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple exams from tracks and make courses/tracks the only commercial products, with track-specific exam ordering and prerequisites.

**Architecture:** Introduce `TrackExam` as the composition boundary between independent `Exam` records and `ExamTrack`. TrackExam owns ordering and prerequisites. Remove exam pricing, exam-to-track FK, and global exam prerequisites. Update access, progression, catalog, admin, checkout, and tests to use the new relationship.

**Tech Stack:** Django ORM, Django admin, existing AccessService, subscription plans, payment services, pytest/Django TestCase patterns already used by the repository.

**Spec:** `docs/superpowers/specs/2026-09-05-independent-exams-track-composition.md`

## Global Constraints

- Exams must be reusable across multiple tracks.
- Track order must not imply prerequisites.
- Pricing exists only for Course and Track.
- No new exam checkout flow.
- Existing development data may be discarded; no compatibility migration is required.

---

### Task 1: Lock the new model contract with tests
**Files:** Create `quiz/test_independent_exam_track_contract.py`.
- [ ] Add failing tests proving an exam has no track/pricing/prerequisite fields and TrackExam supports order/prerequisites.
- [ ] Add tests proving the same exam can be attached to multiple tracks.
- [ ] Run the targeted test locally; expected initial failure because TrackExam does not exist.

### Task 2: Add TrackExam and simplify Exam
**Files:** Create `quiz/models/track_exam.py`; modify `quiz/models/exam.py`, `quiz/models/exam_track.py`, `quiz/models/__init__.py`.
- [ ] Implement TrackExam FK to track/exam, unique track+exam, positive position, and self-referential prerequisites through TrackExam.
- [ ] Validate prerequisites belong to the same track, cannot include self, and position is positive.
- [ ] Remove Exam.track, Exam.prerequisite_exams, Exam.is_free, Exam.price, Exam.currency and obsolete validation/indexes.
- [ ] Remove obsolete ExamTrack subscription-scope values/legacy pricing only where they represent exam commerce; retain track pricing plans.
- [ ] Export TrackExam.
- [ ] Run model contract tests.

### Task 3: Rebuild schema cleanly
**Files:** Create/update `quiz/migrations/0003_independent_exams.py`.
- [ ] Create TrackExam and remove obsolete Exam fields/indexes.
- [ ] Because development data may be discarded, do not add data migration logic.
- [ ] Verify migration dependency chain and model state.

### Task 4: Rewrite track progression/access
**Files:** Modify `quiz/services/track_progress.py`, `subscriptions/services/access_service.py` and related exam access views/tests.
- [ ] Resolve track exams through TrackExam ordered by position.
- [ ] Evaluate only explicitly configured TrackExam prerequisites.
- [ ] Make track entitlement grant access to each included exam.
- [ ] Ensure the same Exam can be accessible through any owned track containing it.
- [ ] Ensure an exam outside an owned track is not unlocked by unrelated track membership.
- [ ] Add regression tests and run targeted suite.

### Task 5: Remove exam commerce and update catalog
**Files:** Modify `payments/views/checkout.py`, `payments/models.py` only if no longer needed, `subscriptions/services/plan_service.py`, `quiz/services/learning_catalog.py`, relevant views/templates/URLs.
- [ ] Remove exam pricing presentation from catalog.
- [ ] Make marketplace product types courses/tracks only.
- [ ] Remove exam checkout route and calls.
- [ ] Remove get_plan_for_exam.
- [ ] Keep exam detail as an assessment/detail surface without purchase pricing.
- [ ] Test course/track pricing and absence of exam commerce.

### Task 6: Update admin workflow
**Files:** Modify `quiz/admin.py` or the current Track admin module and related templates if applicable.
- [ ] Remove track/pricing/prerequisite controls from Exam admin.
- [ ] Add TrackExam inline on Track admin.
- [ ] Allow selecting existing exams, setting order, and selecting TrackExam prerequisites.
- [ ] Ensure prerequisite choices are limited to exams already attached to the same track.
- [ ] Add admin/form regression tests.

### Task 7: Update all remaining consumers and UI
**Files:** Search and modify every remaining reference to `exam.track`, `prerequisite_exams`, exam price/is_free/currency, `track.exams` where composition semantics matter, and exam checkout links.
- [ ] Replace direct relationship assumptions with TrackExam.
- [ ] Update track detail/progress templates and exam detail context.
- [ ] Update payment/access tests.
- [ ] Run repository-wide targeted tests and syntax/model checks available in the environment.

### Task 8: Final verification and delivery
- [ ] Review changed files and diff for stale references.
- [ ] Run available Django test suite; if runtime/CI is unavailable, explicitly report that limitation.
- [ ] Commit implementation.
- [ ] Open PR to `main`.
- [ ] Verify PR diff and merge.
- [ ] Verify `main` points to the merge commit.
