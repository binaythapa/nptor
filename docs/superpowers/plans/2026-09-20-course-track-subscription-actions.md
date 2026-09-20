# Course and Track Subscription Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add consistent Subscribe Free/Buy/Continue Learning actions for courses and tracks, implement instant free enrollment, preserve independent course/track ownership, and surface enrolled resources in My Learning.

**Architecture:** Reuse the existing learning catalog, `AccessService`, subscription plans, enrollment/access models, and My Learning infrastructure. Courses and tracks remain distinct resources: course access unlocks only the course, while track access unlocks the track and all courses contained in that track. Free track enrollment must atomically grant access to the track and its included courses.

**Tech Stack:** Django, existing quiz/course/subscription services, Django templates, existing test framework.

**Spec:** `docs/superpowers/specs/2026-09-20-course-track-subscription-actions-design.md`

## Global Constraints

- Courses and tracks are independent purchasable/subscribable resources.
- A free course subscription is immediate and requires no approval.
- A free track subscription grants access to the track and every included course.
- A course purchase must not unlock its parent track.
- A track purchase must not require separate purchases for included courses.
- Existing paid subscription/payment flows must be reused rather than duplicated.
- Repeated subscriptions must be idempotent and must not create duplicate access records.
- Unauthenticated users must be directed through the existing authentication flow before enrollment or purchase.
- Existing certification and exam-launch behavior must remain functional.

## Review Focus

- A user subscribing to a course that belongs to a track must not receive track access; cover in course-access tests.
- A user subscribing to a track must receive access to every currently included course without duplicate records; cover in track-enrollment tests.
- Repeated clicks or retries must be idempotent; cover in service and request tests.
- Paid resources must never be accidentally enrolled through the free endpoint; cover in action-routing tests.
- Anonymous users and mobile-sized action layouts must remain usable; cover in view/template tests and responsive template review.

### Task 1: Audit Existing Access and Enrollment Interfaces

**Files:**
- Inspect: `subscriptions/services.py`, relevant subscription models/services
- Inspect: `quiz/models.py`, `courses/models.py`
- Inspect: existing My Learning views/templates and URL configuration
- Inspect: existing catalog templates and resource-action patterns
- Test: existing subscription/access tests

**Interfaces:**
- Produces a verified map of existing resource constants, enrollment models, payment entry points, My Learning query methods, and URL names for subsequent tasks.

- [ ] **Step 1: Locate existing access constants and service methods**
  - Identify the exact `AccessService` resource identifiers and access-grant/revoke methods for courses and tracks.
  - Identify the canonical model or service used to represent student ownership/enrollment.
- [ ] **Step 2: Locate existing paid checkout entry points**
  - Record the exact URL names, view signatures, and required parameters for course and track purchases.
- [ ] **Step 3: Locate My Learning aggregation**
  - Record the exact view, context keys, and template partials used to render owned courses and tracks.
- [ ] **Step 4: Run the existing relevant tests**
  - Run the focused subscription, access, catalog, and My Learning tests before changing code.
- [ ] **Step 5: Commit the audit notes if repository documentation is needed**
  - Commit only if a concise implementation note is useful; otherwise carry the verified interfaces into the next task.

### Task 2: Add a Centralized Resource-Action Resolver

**Files:**
- Create or modify: the existing learning-catalog/action service module identified in Task 1
- Modify: `quiz/services/learning_catalog.py` or the project’s established equivalent
- Test: the existing catalog/service test module, or create a focused test module under the project’s established test directory

**Interfaces:**
- Consumes: resource type, resource instance, request user, and existing access/pricing data.
- Produces: a stable action descriptor containing action state, label, URL name/URL, and whether authentication is required.

- [ ] **Step 1: Write failing tests for course action states**
  - Assert that an unauthenticated user sees the appropriate Subscribe Free/Buy state.
  - Assert that an enrolled user sees Continue Learning.
- [ ] **Step 2: Write failing tests for track action states**
  - Assert equivalent states for free and paid tracks.
  - Assert that track ownership is evaluated independently from ownership of an included course.
- [ ] **Step 3: Implement the resolver using existing services**
  - Do not create a second access or payment system.
  - Ensure free/premium classification matches the catalog’s existing pricing rules.
- [ ] **Step 4: Run focused tests and correct failures**
  - Run the exact resolver tests with verbose output.
- [ ] **Step 5: Commit**
  ```bash
  git add <resolved-action-files> <action-tests>
  git commit -m "feat: centralize course and track resource actions"
  ```

### Task 3: Implement Idempotent Instant Free Enrollment

**Files:**
- Create or modify: the established enrollment/access service module
- Modify: existing course and track action views/URL configuration
- Test: focused free-enrollment service and request tests

**Interfaces:**
- Consumes: authenticated user, resource type, and resource ID.
- Produces: an idempotent enrollment result and redirects to the resource’s learning destination.

- [ ] **Step 1: Write failing tests for free-course enrollment**
  - A valid free course creates access once and becomes visible in My Learning.
  - Repeating the request does not create duplicate access/enrollment records.
- [ ] **Step 2: Write failing tests for free-track enrollment**
  - A valid free track grants track access and access to every included course.
  - Repeating the request remains idempotent.
- [ ] **Step 3: Write failing tests for invalid requests**
  - Premium resources cannot be enrolled through the free endpoint.
  - Unauthenticated users are redirected through the existing login flow.
  - Missing, unpublished, or inaccessible resources are rejected using existing conventions.
- [ ] **Step 4: Implement the service transactionally**
  - Use the project’s existing transaction and uniqueness conventions.
  - For tracks, resolve included courses from the canonical track relationship and grant access to the track plus each course.
  - Preserve course/track independence when the resource type is `course`.
- [ ] **Step 5: Wire the endpoint to the resolver and templates**
  - Use POST for state-changing free enrollment if that matches project conventions; include CSRF protection.
- [ ] **Step 6: Run focused tests**
  ```bash
  pytest <free-enrollment-tests> -v
  ```
- [ ] **Step 7: Commit**
  ```bash
  git add <enrollment-files> <enrollment-tests>
  git commit -m "feat: add idempotent free course and track enrollment"
  ```

### Task 4: Connect Paid Buy Actions to Existing Checkout

**Files:**
- Modify: catalog/action resolver and resource-card templates
- Modify: existing course/track checkout URL wiring only where required
- Test: paid-action routing tests

**Interfaces:**
- Consumes: the existing paid checkout endpoints discovered in Task 1.
- Produces: Buy actions that preserve the existing payment flow and return users to My Learning after successful purchase.

- [ ] **Step 1: Write failing tests for paid course and track actions**
  - Premium course cards link to the existing course checkout flow.
  - Premium track cards link to the existing track checkout flow.
  - A paid resource never points to the free-enrollment endpoint.
- [ ] **Step 2: Implement URL/action mapping**
  - Pass the canonical resource identifiers expected by the existing checkout views.
  - Avoid changing payment calculations or gateway behavior.
- [ ] **Step 3: Run focused tests**
  ```bash
  pytest <paid-action-tests> -v
  ```
- [ ] **Step 4: Commit**
  ```bash
  git add <action-and-template-files> <paid-action-tests>
  git commit -m "feat: connect course and track buy actions"
  ```

### Task 5: Add Actions Everywhere Resources Are Rendered

**Files:**
- Modify: `templates/quiz/student/learning_marketplace.html`
- Modify: domain hub/resource-card templates and shared card partials identified in Task 1
- Modify: track detail, course detail, search/list, and recommendation templates that render these resources
- Test: template/view tests for each rendering surface

**Interfaces:**
- Consumes: the centralized action descriptor from Task 2.
- Produces: consistent Subscribe Free, Buy, Continue Learning, and completed-state controls on every course/track card or detail surface.

- [ ] **Step 1: Write failing view/template tests**
  - Assert that each relevant surface renders the correct action for free, paid, owned, and anonymous states.
- [ ] **Step 2: Add a shared action partial**
  - Keep labels and accessibility attributes consistent.
  - Ensure buttons/links expose clear text and do not rely solely on icons.
- [ ] **Step 3: Integrate the partial into every resource surface**
  - Preserve existing card content, filters, and navigation.
  - Ensure course and track actions are based on their own resource type.
- [ ] **Step 4: Review responsive behavior**
  - Check narrow layouts, long titles, and keyboard focus states.
- [ ] **Step 5: Run focused tests and template checks**
  ```bash
  pytest <resource-surface-tests> -v
  ```
- [ ] **Step 6: Commit**
  ```bash
  git add templates <surface-view-files> <surface-tests>
  git commit -m "feat: add consistent resource actions across learning surfaces"
  ```

### Task 6: Update My Learning to Show Owned Courses and Tracks

**Files:**
- Modify: existing My Learning view/service
- Modify: existing My Learning templates and filters/tabs
- Test: My Learning aggregation and visibility tests

**Interfaces:**
- Consumes: canonical access/enrollment records for courses and tracks.
- Produces: independent course and track collections in My Learning, with Continue Learning destinations.

- [ ] **Step 1: Write failing tests**
  - A free course appears after subscription.
  - A subscribed track appears and its included courses are available.
  - A course-only subscription does not display the parent track as owned.
  - A track subscription displays the track independently and does not create duplicate course entries if course access already existed.
  - Unowned marketplace resources do not appear in My Learning.
- [ ] **Step 2: Implement aggregation using existing access services**
  - Avoid direct ad hoc ownership logic where `AccessService` is the established authority.
  - Keep course and track collections distinct.
- [ ] **Step 3: Add or preserve useful grouping and empty states**
  - Include clear sections for courses and tracks without breaking existing certification views.
- [ ] **Step 4: Run focused tests**
  ```bash
  pytest <my-learning-tests> -v
  ```
- [ ] **Step 5: Commit**
  ```bash
  git add <my-learning-files> <my-learning-tests>
  git commit -m "feat: surface subscribed courses and tracks in my learning"
  ```

### Task 7: Regression, Security, and Full Verification

**Files:**
- Modify: only files required by verified test failures
- Test: existing certification, exam launch, access, subscription, and My Learning suites

**Interfaces:**
- Consumes: all implemented action, enrollment, checkout, and My Learning behavior.
- Produces: verified compatibility with existing certification and exam flows.

- [ ] **Step 1: Run all focused feature tests**
  ```bash
  pytest <all-new-and-changed-tests> -v
  ```
- [ ] **Step 2: Run certification and exam regression tests**
  ```bash
  pytest <certification-and-exam-tests> -v
  ```
- [ ] **Step 3: Run the project’s broader test suite**
  ```bash
  pytest
  ```
- [ ] **Step 4: Inspect security-sensitive paths**
  - Verify CSRF protection, authentication checks, authorization checks, object ownership, and premium-resource restrictions.
- [ ] **Step 5: Review the final diff**
  ```bash
  git diff --check
  git diff HEAD~<appropriate-range>..HEAD --stat
  ```
- [ ] **Step 6: Commit any final verified corrections**
  ```bash
  git add <verified-corrections>
  git commit -m "test: verify course and track subscription flows"
  ```
