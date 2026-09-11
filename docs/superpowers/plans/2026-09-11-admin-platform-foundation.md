# NPTOR Admin Platform Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a compact NPTOR platform-admin experience with explicit platform authorization, organization-service request approval, and reusable in-app notifications.

**Architecture:** Keep organization membership/permissions as the organization authorization source of truth, add a platform-admin guard for platform-only operations, introduce a small request domain that activates memberships only after approval, and add a reusable notification domain with actionable in-app delivery first. Replace the dashboard's fragmented KPI-heavy presentation with a small set of platform KPIs plus actionable attention/activity panels.

**Tech Stack:** Django, Django ORM, Django templates, existing NPTOR organization/subscription models, existing admin CSS/navigation, Django tests/migrations.

**Spec:** `docs/superpowers/specs/2026-09-11-admin-platform-foundation.md`

## Global Constraints

- Platform Admin must be distinct from organization Owner/Admin/Staff/Student authorization.
- Organization membership remains the source of truth for organization-level access.
- Organization access requests must be explicitly approved before membership activation.
- Notification creation must be centralized and reusable.
- The dashboard must remain compact and avoid duplicating detailed analytics.
- Subscription/SubscriptionEntitlement is the canonical subscription architecture for the new dashboard.
- All state-changing actions require appropriate authorization and POST/CSRF protection.
- Do not claim tests pass until the actual test commands have been run and results inspected.

---

### Task 1: Establish platform-admin authorization

**Files:**
- Inspect/modify the existing centralized authorization module under `organizations/permissions.py` or the appropriate platform authorization module.
- Modify platform-admin views that currently rely only on Django `is_staff` where applicable.
- Test: existing/new authorization tests in the appropriate `organizations` or platform test package.

**Interfaces:**
- Produces a reusable platform-admin predicate/decorator for platform-only views/actions.
- Must not grant access to organization Staff merely because `is_staff=True`.

- [ ] **Step 1: Write failing authorization tests** for a platform admin, organization staff member, normal student, and unauthenticated request.
- [ ] **Step 2: Run the focused authorization tests and verify the new tests fail for the current behavior.**
- [ ] **Step 3: Implement the centralized platform-admin guard using the repository's existing authorization conventions.**
- [ ] **Step 4: Update platform-admin entry points to use the guard.**
- [ ] **Step 5: Run focused authorization tests and then the organization test suite.**
- [ ] **Step 6: Commit the authorization change.**

### Task 2: Implement organization service request domain

**Files:**
- Create an organization-request model in the appropriate `organizations/models/` module.
- Create migration under `organizations/migrations/`.
- Add service functions under `organizations/services/` for submit/approve/reject/revoke.
- Add model/service tests under `organizations/tests/`.

**Interfaces:**
- `submit_access_request(user, organization, service, requested_role=None, reason="")`
- `approve_access_request(request, reviewer, notes="")`
- `reject_access_request(request, reviewer, notes="")`
- Optional revoke operation if the existing authorization lifecycle requires it.
- Approval must create/reactivate the appropriate `OrganizationMember` transactionally and idempotently.

- [ ] **Step 1: Write failing model tests covering status values, relationships, timestamps, and duplicate-request constraints.**
- [ ] **Step 2: Write failing service tests for submit, approve, reject, duplicate approval, and unauthorized reviewer.**
- [ ] **Step 3: Run the focused tests and verify failures.**
- [ ] **Step 4: Implement the model and migration.**
- [ ] **Step 5: Implement the request service with transaction boundaries and existing membership/role helpers.**
- [ ] **Step 6: Run focused request tests and verify they pass.**
- [ ] **Step 7: Commit the request domain.**

### Task 3: Add user-facing organization service request flow

**Files:**
- Modify organization public/member URLs and views.
- Create request form/template under `organizations/templates/` following existing conventions.
- Add tests for request submission and access restrictions.

**Interfaces:**
- Authenticated users can request supported organization services.
- Existing members should receive an appropriate response rather than creating redundant active membership.
- Submission creates `PENDING` request and triggers a platform-admin notification.

- [ ] **Step 1: Write failing view tests for authenticated submission, anonymous access, duplicate pending request, and existing membership.**
- [ ] **Step 2: Implement the form/view/URL using the request service.**
- [ ] **Step 3: Add concise success/error messaging and request-status visibility to the user.**
- [ ] **Step 4: Run focused view tests.**
- [ ] **Step 5: Commit the user request flow.**

### Task 4: Build reusable notification domain and in-app center

**Files:**
- Create notification model under an appropriate app/domain location.
- Create migration.
- Create notification service/helpers.
- Add notification URLs/views/templates.
- Modify `templates/layouts/admin/header_admin.html` and shared authenticated navigation as needed.
- Add CSS/JS only where existing patterns require it.
- Add notification tests.

**Interfaces:**
- `create_notification(recipient, notification_type, title, message, priority="info", target_url=None, metadata=None)`
- `mark_notification_read(notification)`
- Query helper for unread notifications and recent notifications.
- Initial delivery channel is in-app; channel abstraction must not block later email/SMS.

- [ ] **Step 1: Write failing tests for creation, unread count, read transition, recipient isolation, priority, and actionable target.**
- [ ] **Step 2: Run focused tests and verify failure.**
- [ ] **Step 3: Implement the model/migration and service.**
- [ ] **Step 4: Implement notification list/read endpoints with proper authentication and authorization.**
- [ ] **Step 5: Add compact header unread indicator and notification center UI.**
- [ ] **Step 6: Run focused notification tests.**
- [ ] **Step 7: Commit notification foundation.**

### Task 5: Connect organization request events to notifications

**Files:**
- Modify organization request service.
- Add/update notification tests.
- Add admin/user templates if needed for actionable links.

**Interfaces:**
- New pending request notifies eligible platform admins.
- Approval/rejection notifies requester.
- Approved access points to the relevant organization workspace/service.

- [ ] **Step 1: Add failing event-notification tests for each request transition.**
- [ ] **Step 2: Emit notifications from the request service only after successful state changes.**
- [ ] **Step 3: Verify duplicate/retried operations do not spam duplicate notifications.**
- [ ] **Step 4: Run request + notification integration tests.**
- [ ] **Step 5: Commit integration.**

### Task 6: Add platform-admin request center

**Files:**
- Create admin request views/forms/templates under the appropriate admin namespace.
- Modify platform/admin URLs.
- Add request-center tests.

**Interfaces:**
- List pending/recent requests with filters for status/service/organization.
- Detail page exposes requester, organization, requested service/role, reason, timestamps, and prior review state.
- Approve/reject are POST actions protected by platform-admin authorization.

- [ ] **Step 1: Write failing tests for list visibility, filtering, detail visibility, approve/reject permissions, and CSRF-safe POST behavior.**
- [ ] **Step 2: Implement URLs/views/templates using the request service.**
- [ ] **Step 3: Add dashboard-compatible pending-request count helper.**
- [ ] **Step 4: Run focused request-admin tests.**
- [ ] **Step 5: Commit the admin request center.**

### Task 7: Redesign the platform-admin dashboard compactly

**Files:**
- Modify `quiz/views/dashboards.py` or extract a focused admin-dashboard service if the existing view remains too large.
- Modify `templates/quiz/admin/admin_dashboard.html`.
- Modify relevant admin CSS only as needed.
- Add dashboard tests.

**Interfaces:**
- Primary KPIs: users, organizations, courses, exams, revenue.
- Secondary panels: Needs Attention, Recent Activity, subscriptions/revenue, organizations snapshot.
- Pending organization requests are a first-class attention metric.
- Avoid legacy CourseSubscription metrics in the new dashboard; use canonical Subscription/SubscriptionEntitlement data.

- [ ] **Step 1: Write failing tests for the compact dashboard context and platform-admin access.**
- [ ] **Step 2: Extract only the metrics required by the new layout; remove redundant/legacy dashboard calculations.**
- [ ] **Step 3: Implement the compact template hierarchy.**
- [ ] **Step 4: Add Needs Attention links to requests/reviews/payment issues that have real routes.**
- [ ] **Step 5: Add Recent Activity using the notification/audit data available in the repository without creating a second event system unnecessarily.**
- [ ] **Step 6: Run dashboard tests and template checks.**
- [ ] **Step 7: Commit the dashboard redesign.**

### Task 8: Simplify admin navigation and integrate notifications

**Files:**
- Modify `templates/layouts/admin/sidebar_admin.html`.
- Modify `templates/layouts/admin/header_admin.html`.
- Modify navigation CSS/JS only as required.
- Add navigation/template tests if the project has a suitable test pattern.

**Interfaces:**
- Compact navigation exposes Dashboard, Users, Organizations, Requests, Courses, Exams, Questions, Subscriptions, Payments, Reports, Activity Log.
- Notification bell remains visible without consuming major header space.
- Avoid dead links; every newly displayed route must exist before navigation is merged.

- [ ] **Step 1: Inventory current URL names for each navigation target.**
- [ ] **Step 2: Update sidebar grouping and remove unrelated authoring/practice items from the core platform-admin navigation.**
- [ ] **Step 3: Add request pending badge and notification unread badge using server-side counts.**
- [ ] **Step 4: Verify all template URL reversals resolve.**
- [ ] **Step 5: Commit navigation changes.**

### Task 9: Notification preferences and extensible delivery channels

**Files:**
- Add preference model only if the existing repository has no reusable preference mechanism.
- Add migration if required.
- Add settings views/templates and tests.

**Interfaces:**
- Per-category preferences for non-critical notifications.
- In-app is always available.
- Email/SMS adapters remain interfaces/hooks rather than mandatory providers.

- [ ] **Step 1: Write failing preference tests.**
- [ ] **Step 2: Implement minimal preference persistence and service checks.**
- [ ] **Step 3: Add user settings UI only where it provides real value.**
- [ ] **Step 4: Run focused tests.**
- [ ] **Step 5: Commit preferences.**

### Task 10: End-to-end regression and verification

**Files:**
- Modify tests only for discovered regressions.

- [ ] **Step 1: Run organization tests.**
- [ ] **Step 2: Run relevant accounts/quiz/courses/subscriptions tests.**
- [ ] **Step 3: Run the full test suite with the repository's configured command.**
- [ ] **Step 4: Inspect failures and fix only verified regressions.**
- [ ] **Step 5: Re-run all affected suites.**
- [ ] **Step 6: Inspect Git diff and migration consistency.**
- [ ] **Step 7: Commit final integration and prepare a PR.**
