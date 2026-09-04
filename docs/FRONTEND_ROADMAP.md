# NPTOR Frontend Roadmap

## Purpose and current architecture

NPTOR is a server-rendered Django 6 LMS and examination platform. The frontend should expose existing backend capabilities without duplicating business rules in templates or JavaScript.

The application currently has three frontend experiences:

1. Student portal — shared shell in `templates/layouts/student/`, with learning, practice, exams, profile, and commerce pages.
2. Organization administration — organization-scoped templates in `templates/organizations/admin/` and permission-aware views under `organizations/views/admin/`.
3. Platform administration — custom administration pages under `templates/quiz/admin/` and the admin shell in `templates/layouts/admin/`; Django Admin remains the super-admin fallback.

Shared styling is based on `static/css/theme.css`, `base.css`, `layout.css`, `components.css`, and `responsive.css`, supplemented by page-specific CSS and lightweight JavaScript in `static/js/`.

## Frontend principles

- Preserve useful backend behavior and authorization boundaries.
- Prefer shared shell, component, CSS, and JavaScript patterns over page-specific duplication.
- Design for desktop, tablet, and mobile; do not optimize only for screenshots.
- Make important actions understandable, keyboard-usable, and accessible.
- Include appropriate loading, empty, error, and access-denied states where the backend supports them.
- Do not introduce a frontend framework or build system without explicit approval.

## Portal architecture

### Student portal

Existing student-facing capabilities include:

- Dashboard and unified learning activity for courses, exams, and tracks.
- Course catalog, detail/preview, player, lessons, progress, and certificates where supported.
- Practice and Practice Express question flows.
- Exam catalog, preview, locked state, attempt, final review, result, and answer review.
- Profile, authentication, notifications, shortlists, study plans, subscriptions, and checkout/payment pages.

The student navigation should progressively expose only supported functionality:

- Dashboard
- Learning: courses, continuation, completion, and lessons
- Practice: standard practice and Practice Express
- Exams: tracks, catalog, attempts, results, and answer review
- Commerce: plans, subscriptions, orders, payments, and coupons where applicable
- Account: profile, security, and supported preferences

### Organization administration

Organization administration is scoped through memberships, roles, `request.organization`, middleware, and permission helpers. It currently has views/templates for dashboard, students/members, assignments, courses, exams, tracks, questions, categories, domains, and settings.

Organization UI must never substitute frontend filtering for backend access checks. Future organization work should keep every resource query and mutation constrained to the active organization.

### Platform administration

The custom platform-admin interface is the normal operational interface; Django Admin remains available for low-level super-admin work. Existing custom administration covers dashboards, questions, users, subscriptions, pricing, payments, coupons, and related management flows.

The target navigation groups are users, organizations, learning, exams, commerce, reports, and settings, but a page should be added only after its underlying backend operation and authorization are confirmed.

## Shared design system

Before adding new page families, consolidate and reuse these patterns:

- app shells, responsive headers, sidebars, and mobile navigation;
- breadcrumbs and page headers;
- cards, buttons, badges, alerts, modals, and confirmation dialogs;
- forms, inputs, selects, validation, and permission feedback;
- tables, tabs, search, filters, pagination, and dropdowns;
- empty, loading, error, and access-denied states.

Use the existing shared CSS layers first. Keep feature CSS scoped to its page namespace, as the exam and practice styles already do.

## Critical user flows

### Exams

The intended exam flow is:

```text
Exam catalog → preview → start → questions → editable final review
→ confirm and submit → student dashboard → answer review
```

Requirements:

- final review remains editable before submission;
- submission locks the `UserExam` and is idempotent for already submitted attempts;
- the submit route handles direct GET safely rather than returning HTTP 405;
- the dashboard exposes read-only answer review after submission;
- the timer preserves saved answers on expiry, submits/locks the attempt, and keeps result/review available;
- question and choice order remain stable within an attempt across navigation and refresh.

### Courses

The supported course journey is catalog → detail/preview → enrollment or purchase → course player → section/lesson → progress/completion → certificate where enabled. Frontend changes must use the existing course, progress, quiz-completion, and access services rather than recreate those rules.

### Commerce

Commerce follows resource → pricing → coupon → checkout → payment → order → subscription/entitlement. Templates and JavaScript must call established checkout, payment, fulfillment, and subscription flows instead of reproducing payment logic.

### Organizations

Organization work encompasses memberships, roles, groups where supported, assignments, courses, exams, tracks, and progress/reporting. Every organization page must respect the existing ownership and authorization layer.

## Development phases

| Phase | Focus | Current status |
| --- | --- | --- |
| 0 | Shared design system, shells, responsive/permission-aware navigation, common states | Foundations and student/admin shells exist; consolidation should precede broad page expansion. |
| 1 | Student core: dashboard, courses, learning, lessons, profile | Core pages exist; improve consistently without regressing learning activity. |
| 2 | Exams: catalog through answer review | Existing flow is present; timer expiry and deterministic choice ordering are current correctness priorities. |
| 3 | Practice and Practice Express | Existing flows and page assets exist; continue consistency and accessibility work. |
| 4 | Commerce | Payments, checkout, subscriptions, plans, and coupons are present; surface only verified operations. |
| 5 | Organization portal | Core scoped administration exists; expand only within established boundaries. |
| 6 | Platform admin | Custom management pages exist; evolve toward complete normal-admin coverage while retaining Django Admin fallback. |
| 7 | Polish | Responsive QA, accessibility, states, performance, UX consistency, and security review. |

## Acceptance criteria for future frontend work

Each change should demonstrate that:

1. It maps to an existing backend capability and respects authorization.
2. It reuses the appropriate shell and shared frontend pattern.
3. It works on desktop, tablet, and mobile as applicable.
4. It has clear primary action, empty/error/access behavior, and keyboard-usable controls where relevant.
5. Existing student learning activity, course, practice, exam, commerce, and organization flows are not regressed.
6. Targeted tests, related tests, Django system checks, and final diff review have actual recorded results.

## Current status and next focus

The project already contains substantial student, organization, and custom-admin frontend coverage. The immediate development priority is correctness in the existing exam experience: stable per-attempt choice ordering and safe expiry submission that grades saved answers without altering the dashboard-first submission flow.

This roadmap is a planning document. It does not claim that future phases, page coverage, design-system consolidation, or the identified exam correctness work have been implemented.
