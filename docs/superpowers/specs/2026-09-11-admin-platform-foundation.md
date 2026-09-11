# NPTOR Admin Platform Foundation

## Goal
Build a compact, industry-standard NPTOR platform-admin experience with explicit platform authorization, organization-service requests, and a reusable notification system.

## Principles
- Platform Admin is distinct from organization Owner/Admin/Staff/Student roles.
- Organization access is granted through an explicit request and approval workflow.
- Approved requests create or activate organization membership; authorization is never inferred from URL access or Django `is_staff` alone.
- Notifications are actionable, prioritized, and reusable by future academic, exam, attendance, subscription, and system workflows.
- The admin dashboard remains compact; detailed analytics belong on dedicated pages.
- Existing organization permission helpers and membership model remain the source of truth for organization authorization.
- Existing Subscription/SubscriptionEntitlement architecture is canonical for subscription analytics; legacy CourseSubscription metrics should not drive the new dashboard.

## Dashboard
Primary KPIs:
1. Users
2. Organizations
3. Courses
4. Exams
5. Revenue

Secondary compact panels:
- Needs Attention: pending organization requests, pending course reviews, payment/system issues where available.
- Recent Activity: recent meaningful platform events.
- Subscription/Revenue summary.
- Organizations snapshot.

## Platform Admin Authorization
Use a centralized platform-admin predicate/decorator for platform-only pages and actions. Organization Staff must not gain platform-admin access merely because Django `is_staff` is true.

## Organization Service Requests
A request records:
- requester/user
- organization
- requested service
- requested role when applicable
- status (`pending`, `approved`, `rejected`, `revoked`)
- optional reason
- requester timestamp
- reviewer/admin
- reviewed timestamp
- review notes

Lifecycle:
`PENDING -> APPROVED -> ACTIVE` or `PENDING -> REJECTED`; active authorization may later be revoked.

Initial service can be `ORGANIZATION_ACCESS`; the model should allow additional service types without redesign.

Approval must be transactional and idempotent: create/reactivate the appropriate `OrganizationMember`, preserve existing role semantics, and record reviewer/audit information. Reject/approve operations must be platform-admin-only.

## Notifications
Provide a reusable notification model/service with:
- recipient
- category/type
- title/message
- priority (`info`, `success`, `warning`, `critical`)
- read state and timestamp
- created timestamp
- optional target URL/object metadata for actionable navigation

Provide an in-app notification center and header unread indicator. Notification creation should be centralized so future features can emit notifications consistently.

Initial events:
- new organization service request -> platform admins
- organization request approved/rejected -> requester
- organization membership/service activated -> requester
- course review required -> platform admins where existing workflow supports it
- important payment/subscription events where existing workflows support them

Notification preferences should support per-category/per-channel preferences where practical, while critical security/system notices remain mandatory. Email/SMS delivery should use an extensible channel abstraction; do not require an external provider for the initial in-app implementation.

## Navigation
Target compact platform-admin navigation:

Dashboard

PLATFORM
- Users
- Organizations
- Requests

CONTENT
- Courses
- Exams
- Questions

BUSINESS
- Subscriptions
- Payments

ANALYTICS
- Reports

SYSTEM
- Activity Log

Existing authoring/practice links should not be exposed as core platform-admin navigation unless their current authorization and purpose require them.

## Auditability and Safety
- Every request decision records reviewer and timestamp.
- Approval/rejection/revocation is protected by platform-admin authorization and POST/CSRF-safe actions.
- Duplicate pending/active access requests should be prevented or handled idempotently.
- Tests must cover unauthorized users, organization staff, platform admins, duplicate requests, approval, rejection, notification creation, unread/read state, and dashboard counts.
