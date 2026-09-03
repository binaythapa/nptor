# Learning Start + Shortlist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let students start learning resources before purchase through controlled previews, encounter an authoritative paywall when full access is required, and save courses/exams/tracks to a persistent dashboard shortlist.

**Architecture:** Keep paid access authoritative through `AccessService`; add a small `LearningShortlist` model with explicit nullable course/track/exam references and a uniqueness constraint per user/resource. Course previews use the existing first-lesson preview mechanism without granting progress; exam previews use a bounded preview page rather than creating a real attempt, and all paid transitions preserve a return target for checkout/resume.

**Tech Stack:** Django ORM, existing `AccessService`, existing course/exam/payment views, Django templates, vanilla JavaScript, existing quiz test suite.

**Spec:** `docs/superpowers/specs/2026-09-04-learning-marketplace-design.md` plus the approved Start → Preview → Paywall → Checkout → Resume and Shortlist design from the conversation.

## Global Constraints

- Public marketplace resources remain limited to approved/published/public platform resources.
- `AccessService` remains the authoritative source for purchased/assigned access.
- Shortlisting never grants access and must respect resource visibility when rendered.
- Preview mode must not create lesson progress, certificates, paid exam attempts, or resource access.
- Paid checkout remains POST/ownership scoped and must not bypass payment fulfillment.
- Mutating shortlist endpoints are POST-only and CSRF protected.
- Preserve responsive/accessibility behavior and do not introduce frontend dependencies.
- Runtime Django verification is required when an executable environment is available; otherwise report the limitation without claiming tests passed.

---

### Task 1: Add the persistent shortlist model and regression tests

**Files:**
- Create: `quiz/models/learning_shortlist.py`
- Modify: `quiz/models/__init__.py`
- Create: `quiz/migrations/0002_learningshortlist.py`
- Test: `quiz/test_learning_shortlist.py`

**Interfaces:**
- Produces `LearningShortlist` with `user`, `resource_type`, and nullable `course`, `track`, `exam` references.
- Produces `LearningShortlist.for_resource(user, resource_type, resource)` and `LearningShortlist.remove_for_resource(...)` helpers.

- [ ] **Step 1: Write failing tests** for create, uniqueness, resource-type validation, and removal.
- [ ] **Step 2: Run the shortlist tests and confirm they fail because the model does not exist.**
- [ ] **Step 3: Implement the model with a DB uniqueness constraint and model validation requiring exactly one matching resource FK.**
- [ ] **Step 4: Add the migration.**
- [ ] **Step 5: Run the shortlist tests again.**
- [ ] **Step 6: Commit `feat: add learning shortlist model`.**

---

### Task 2: Add secure shortlist endpoints and marketplace integration

**Files:**
- Create: `quiz/views/learning_shortlist.py`
- Modify: `quiz/urls/urls.py`
- Modify: `quiz/services/learning_catalog.py`
- Modify: `quiz/views/learning_marketplace.py`
- Modify: `templates/quiz/student/learning_marketplace.html`
- Modify: `templates/quiz/student/domain_hub.html`
- Create: `static/js/pages/learning_shortlist.js`
- Modify: `static/css/pages/learning_marketplace.css`
- Test: `quiz/test_learning_shortlist_views.py`

**Interfaces:**
- `POST /quiz/learning/shortlist/<resource_type>/<id>/` toggles a visible course/track/exam shortlist entry.
- `LearningShortlist` state is exposed as `is_shortlisted` on catalog resource items.

- [ ] **Step 1: Write failing view tests** for login requirement, POST-only mutation, visibility scoping, toggle behavior, and dashboard/catalog state.
- [ ] **Step 2: Run the tests and confirm the expected failures.**
- [ ] **Step 3: Implement the POST-only toggle endpoint using the same public catalog visibility rules before creating a shortlist row.**
- [ ] **Step 4: Add shortlist state to catalog items using one user-scoped query instead of one query per card.**
- [ ] **Step 5: Add bookmark controls with accessible labels and AJAX toggle behavior; keep a non-JS form fallback.**
- [ ] **Step 6: Run the tests and commit `feat: add learning shortlist controls`.**

---

### Task 3: Surface shortlist in the student dashboard

**Files:**
- Modify: `quiz/views/student_learning_dashboard.py`
- Modify: `templates/quiz/student/student_dashboard.html`
- Modify: `static/css/pages/dashboard_learning_hub.css`
- Create: `static/js/pages/dashboard_shortlist.js`
- Test: `quiz/test_student_learning_dashboard_shortlist.py`

**Interfaces:**
- Dashboard context exposes `shortlist_items` and `shortlist_count`.
- Each item includes resource type, title, access state, and an action URL.

- [ ] **Step 1: Write failing tests** proving shortlisted resources appear for their owner, unauthorized users cannot see another user's shortlist, and deleted/unpublished resources are omitted.
- [ ] **Step 2: Run the tests and confirm the expected failures.**
- [ ] **Step 3: Query the user's shortlist once, resolve valid public resources, and merge current `AccessService` access state.**
- [ ] **Step 4: Add a compact `Your Shortlist` section below Continue Learning with remove controls.**
- [ ] **Step 5: Add accessible AJAX removal with a server-rendered fallback.**
- [ ] **Step 6: Run the dashboard shortlist tests and commit `feat: show learning shortlist on dashboard`.**

---

### Task 4: Implement controlled course preview and paywall/resume

**Files:**
- Modify: `courses/views/student_views.py`
- Modify: `templates/courses/student/course_detail.html`
- Modify: `templates/courses/student/course_player.html`
- Test: `courses/test_student_course_preview.py`

**Interfaces:**
- Public non-owner users can start the course preview without an entitlement.
- Only the first lesson is previewable by default; subsequent lesson access requires `AccessService.has_access`.
- Locked lesson navigation redirects to the course paywall/checkout while preserving the course slug and lesson target.

- [ ] **Step 1: Write failing tests** for preview access, no-progress/no-certificate behavior, locked second lesson, and paid-user unrestricted access.
- [ ] **Step 2: Run the tests and confirm the expected failures.**
- [ ] **Step 3: Add a student-safe preview mode that permits only the first ordered lesson without creating `LessonProgress`.**
- [ ] **Step 4: Gate non-preview lessons with `AccessService.has_access`; preserve owner/admin preview behavior unchanged.**
- [ ] **Step 5: Render a clear paywall CTA that links to the existing course subscription/checkout flow and includes a safe return target.**
- [ ] **Step 6: Run the course preview tests and commit `feat: add course preview paywall`.**

---

### Task 5: Add bounded exam preview and paid continuation

**Files:**
- Modify: `quiz/views/exams.py`
- Modify: `quiz/urls/urls.py`
- Create or modify: `templates/quiz/student/exam/exam_preview.html`
- Test: `quiz/test_exam_preview_access.py`

**Interfaces:**
- A public paid exam can be opened in preview mode without creating `UserExam` or consuming an attempt.
- Preview shows a small bounded sample of questions and a CTA to the existing checkout flow.
- Real `exam_start` remains entitlement-protected for paid exams.

- [ ] **Step 1: Write failing tests** for paid preview visibility, no attempt creation, sample limit, and real exam-start authorization.
- [ ] **Step 2: Run the tests and confirm the expected failures.**
- [ ] **Step 3: Implement the preview view using published exam visibility and a deterministic small question sample.**
- [ ] **Step 4: Add `Try Exam` / `Get Full Access` actions and preserve a safe exam return target.**
- [ ] **Step 5: Run the exam preview tests and commit `feat: add exam preview paywall`.**

---

### Task 6: Final regression and deployment verification

**Files:**
- Modify: relevant test files only if regressions are found.
- Modify: `docs/superpowers/plans/2026-09-04-learning-start-shortlist.md` to mark completed steps.

- [ ] **Step 1: Run `python manage.py check`.**
- [ ] **Step 2: Run the focused shortlist, marketplace, dashboard, course-preview, and exam-preview test modules.**
- [ ] **Step 3: Run the existing payment/access regression tests.**
- [ ] **Step 4: Inspect the final GitHub diff and verify every mutation endpoint is CSRF/POST protected.**
- [ ] **Step 5: Commit any final fixes as focused maintenance commits.**
- [ ] **Step 6: Report exact verification results and whether `migrate` is required.**
