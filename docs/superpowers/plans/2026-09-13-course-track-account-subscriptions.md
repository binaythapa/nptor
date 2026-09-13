# Course, Track, and Account Subscriptions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Courses and Tracks the only directly sellable learning products, connect reusable Exams to both independently, isolate Course/Track subscriptions, and add all-access or quota-based account subscriptions.

**Architecture:** Keep one centralized subscription engine. Add `CourseExam` as the Course↔Exam join while retaining `TrackExam`; add explicit plan product/access modes; represent limited account choices explicitly and evaluate all-access dynamically; centralize Course/Track/Exam authorization in `AccessService` without conflating organization access.

**Tech Stack:** Django 6, existing subscriptions/payments/quiz/courses apps, server-rendered Django templates, existing test framework, MySQL-compatible migrations.

**Spec:** `docs/superpowers/specs/2026-09-13-course-track-account-subscriptions-design.md`

## Global Constraints

- Courses and Tracks remain independent; never add Course↔Track.
- Exams are reusable and never independently purchasable.
- Course subscriptions grant only Course access; Track subscriptions grant only Track access.
- Account plans grant all resources or user-selected Course/Track quotas.
- Organization access remains separate and tenant-scoped.
- Preserve established behavior outside this subscription/product change.
- Do not install dependencies or alter database settings.
- Use additive/non-destructive migration steps and retain compatibility only where needed for existing data.

---

### Task 1: Add reusable Course↔Exam relationship

**Files:**
- Create: `courses/models/course_exam.py`
- Modify: `courses/models/__init__.py`
- Modify: `quiz/models/exam.py`
- Create: `courses/migrations/<next migration>.py`
- Test: existing course/quiz model test modules, plus focused new regression tests where the repository pattern places them.

**Interfaces:**
- Produces `CourseExam(course, exam, order, is_required)` with uniqueness on `(course, exam)`.
- Produces `Course.course_exams` and `Exam.course_memberships` relations.

- [ ] Add failing tests proving one Exam can belong to multiple Courses and duplicate membership is rejected.
- [ ] Run the focused tests and confirm the new relationship is absent/failing.
- [ ] Implement `CourseExam` using the same organization-consistency pattern as `TrackExam`.
- [ ] Add migration and exports.
- [ ] Run model tests and `manage.py check`.
- [ ] Commit `feat: add reusable course exam relationship`.

### Task 2: Make SubscriptionPlan explicit about product and access mode

**Files:**
- Modify: `subscriptions/models/plan.py`
- Create: `subscriptions/migrations/<next migration>.py`
- Modify: subscription plan tests.

**Interfaces:**
- Adds `product_type` values `course`, `track`, `account`.
- Adds `access_mode` values `single_resource`, `limited_access`, `all_access`.
- Adds nullable `max_courses` and `max_tracks` for account quota plans.
- Keeps existing `scope` temporarily for compatibility and maps legacy resource/all-access values safely.

- [ ] Add failing tests for product/mode validation and account quota validation.
- [ ] Implement fields and model validation: Course/Track use single-resource; account uses limited/all-access; limited quotas must be non-negative and have at least one positive quota.
- [ ] Add migration with safe defaults for existing plans based on current scope/attachments.
- [ ] Run focused plan tests.
- [ ] Commit `feat: model subscription plan product types`.

### Task 3: Add limited account resource selections

**Files:**
- Create: `subscriptions/models/account_selection.py`
- Modify: `subscriptions/models/__init__.py`
- Create: `subscriptions/services/account_access_service.py`
- Create: `subscriptions/migrations/<next migration>.py`
- Test: new account subscription service tests.

**Interfaces:**
- `AccountSubscriptionSelection(subscription, course=None, track=None)` stores one selected Course or Track per row.
- `AccountAccessService.select_course(subscription, course)` and `select_track(subscription, track)` enforce an active account subscription and plan quotas transactionally.
- `AccountAccessService.has_course_access(user, course)` and `has_track_access(user, track)` evaluate valid account subscriptions and selections.

- [ ] Add failing tests for selecting Courses/Tracks under quota, duplicate selection, wrong product type, expired subscription, and over-quota rejection.
- [ ] Implement transaction-safe selection with row locking on the subscription and duplicate protection.
- [ ] Implement all-access evaluation without creating per-resource rows.
- [ ] Run focused account tests.
- [ ] Commit `feat: add account subscription resource selections`.

### Task 4: Remove Exam as a subscription product

**Files:**
- Modify: `quiz/models/exam.py`
- Modify: `subscriptions/models/entitlement.py`
- Modify: `subscriptions/services/plan_service.py`
- Create: `subscriptions/migrations/<next migration>.py`
- Modify: affected subscription/quiz tests.

**Interfaces:**
- Subscription entitlements become Course/Track product entitlements.
- `get_plan_for_course()` and `get_plan_for_track()` require matching product type.
- `get_plan_for_exam()` is removed from active purchasing flow; compatibility code must not make an Exam independently purchasable.

- [ ] Add failing tests proving an Exam cannot be attached/selected as a sellable subscription product and Course/Track plan matching is enforced.
- [ ] Remove the persisted Exam subscription M2M after verifying legacy callers and migrate old links without silently creating standalone purchases.
- [ ] Keep only temporary in-memory Exam compatibility properties needed by existing non-purchasing callers.
- [ ] Run focused subscription and quiz tests.
- [ ] Commit `refactor: remove standalone exam subscriptions`.

### Task 5: Centralize subscriber access and inheritance

**Files:**
- Modify: `subscriptions/services/access_service.py`
- Modify: `subscriptions/services/account_access_service.py`
- Modify: Course/Track/Exam access callers and tests discovered by repository search.

**Interfaces:**
- `AccessService.has_course_access(student, course)` checks direct Course access, account access, and existing organization access.
- `AccessService.has_track_access(student, track)` checks direct Track access, account access, and existing organization access.
- `AccessService.has_exam_access(student, exam)` checks legitimate direct legacy/admin access plus parent Course OR parent Track access.
- `AccessService.has_access()` delegates to the typed helpers.

- [ ] Add failing isolation tests: Course A subscription cannot unlock Track B; Track B subscription cannot unlock Course A; shared Exam is accessible through either legitimately owned parent.
- [ ] Add failing tests for account all-access and limited selections.
- [ ] Implement typed authorization and parent membership queries.
- [ ] Preserve organization ResourceAccess behavior and tenant scoping.
- [ ] Run all access/subscription/organization tests.
- [ ] Commit `feat: centralize course track exam authorization`.

### Task 6: Update checkout and subscription fulfillment

**Files:**
- Modify: payment/subscription checkout services and views identified by search for `get_plan_for_exam`, `exam.subscription_plans`, `SubscriptionEntitlement.RESOURCE_EXAM`, and direct Exam purchase URLs.
- Modify: related forms/templates/tests.

**Interfaces:**
- Checkout accepts Course, Track, or Account products only.
- Course/Track purchases create access to the purchased resource only.
- Account purchases create the account subscription; limited plans then use selection service.

- [ ] Add failing checkout tests for product type enforcement and isolation.
- [ ] Update fulfillment to grant Course/Track entitlements or account subscription records.
- [ ] Remove standalone Exam purchase paths.
- [ ] Run payment/subscription tests.
- [ ] Commit `feat: enforce subscription product boundaries`.

### Task 7: Rework custom administration

**Files:**
- Modify: `quiz/views/admin_subscription_views.py`
- Modify: associated admin subscription URLs/templates/forms/tests.

**Interfaces:**
- Admin subscription UI manages Course, Track, and Account subscriptions.
- Exam subscribe/revoke/expiry actions are removed from the purchasable-product workflow.
- Account quota selections use the centralized account access service.

- [ ] Add/update view tests for Course, Track, and Account actions and absence of standalone Exam purchase actions.
- [ ] Implement UI and backend validation.
- [ ] Run focused admin subscription tests.
- [ ] Commit `feat: update subscription administration products`.

### Task 8: Update catalog and exam presentation

**Files:**
- Modify: catalog/preview/dashboard views and templates found by repository search for standalone exam purchase/pricing.
- Modify: relevant CSS only if existing layout requires it.
- Test: catalog and access tests.

**Interfaces:**
- Courses and Tracks are catalog products.
- Exams are shown as children of accessible Courses/Tracks and are not presented as purchasable products.
- Direct exam URLs remain safe and deny access without a valid parent/direct administrative authorization.

- [ ] Add regression tests for catalog visibility and direct exam authorization.
- [ ] Update templates/views using the existing server-rendered shells.
- [ ] Run focused catalog/exam tests.
- [ ] Commit `feat: align catalog with course and track products`.

### Task 9: Remove obsolete duplicate Course plan model and legacy references safely

**Files:**
- Inspect: `courses/models/plan.py`, `courses/models/__init__.py`, all imports/references.
- Modify/delete only after repository-wide reference verification.
- Modify: migrations only if an obsolete model is actually installed.

- [ ] Search all references to the duplicate `courses.models.plan.SubscriptionPlan`.
- [ ] If unused, rename it to a clearly deprecated “to be deleted” compatibility artifact first rather than immediately deleting it.
- [ ] Run tests and checks.
- [ ] Delete only when no references/data remain and the migration state is safe.
- [ ] Commit `chore: retire duplicate course subscription model`.

### Task 10: Migration/data verification and full regression

**Files:**
- Modify/create migration and data migration files required by the preceding tasks.
- Modify tests for migration compatibility.

- [ ] Run `venv\\Scripts\\python.exe manage.py check`.
- [ ] Run focused course/quiz/subscription/payment/organization tests.
- [ ] Run migration tests or `manage.py migrate --plan` without applying destructive changes.
- [ ] Run the full suite `venv\\Scripts\\python.exe manage.py test --noinput -v 2` when the environment is available.
- [ ] Inspect `git status --short`, `git diff --stat`, and `git diff`; verify no secrets and no unrelated files.
- [ ] Commit `test: verify course track account subscription architecture` only if the verification changes are necessary; otherwise report the existing verification commit SHAs.
