# Learning Marketplace Implementation Plan

> **For agentic workers:** execute this plan task-by-task with TDD and verification checkpoints.

## Goal
Implement the approved NPTOR learning marketplace architecture in controlled phases, starting with the catalog UX and access-state clarity while preserving current business rules.

## Phase 1 — Catalog UX
1. Add regression tests for resource-card semantics: type, metrics, pricing/access state, owned state, free state, preview state, locked messaging hooks and wishlist.
2. Extend `quiz/services/learning_catalog.py` to provide presentation-ready metadata for Course, Track and Exam without changing access decisions.
3. Redesign `templates/quiz/student/learning_marketplace.html` with differentiated Course/Track/Exam cards, clear Free/Premium/Purchased/Preview labels, track contents summary and accessible wishlist actions.
4. Refine marketplace CSS for responsive cards, pricing blocks, badges, lock messaging and primary CTAs.
5. Verify the focused catalog tests and inspect the rendered structure/diff.

## Phase 2 — Course detail
1. Protect existing course access/progress behavior with tests.
2. Add a professional sales/learning split, preview labels, curriculum states, outcomes, instructor and related track/exam CTA.
3. Keep enrollment and learning URLs unchanged.

## Phase 3 — Track detail and locking
1. Add a track-item abstraction only if existing schema cannot express ordered lock policy cleanly.
2. Implement ordered exams, progress, prerequisite messaging, minimum-score locks and optional admin/time policies.
3. Add tests for every lock transition before changing enforcement.

## Phase 4 — Exam UX
1. Add exam detail/rules page and tests.
2. Improve attempt/result/review/retry flows without changing grading semantics.
3. Add clear remaining-attempt and lock states.

## Phase 5 — Commerce
1. Audit existing checkout/order/subscription flow.
2. Add resource-agnostic checkout presentation and payment lifecycle states.
3. Grant entitlement only after verified payment success.
4. Add tests for duplicate purchase, failed payment, successful payment and access propagation.

## Phase 6 — Student ecosystem
1. Wishlist page and reusable saved-resource component.
2. My Courses, My Tracks, My Exams and certificates.
3. Dashboard continuation cards and cross-resource recommendations.

## Constraints
- No speculative payment gateway changes.
- No model migration until required by a tested phase.
- Preserve existing access service behavior until replacement behavior has tests.
- Preserve course completion, video tracking, quiz grading, practice flow and certificate issuance.
- Use existing blue LMS visual language.
