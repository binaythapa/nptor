# NPTOR Development Guide

## Project map

NPTOR is a Django 6 learning and examination platform rooted at this directory.

- `objective_exam/` — project configuration and root routing.
- `accounts/` — registration, authentication, profiles, OTP, and account security.
- `courses/` — courses, sections, lessons, enrollments, learning progress, and certificates.
- `organizations/` — organizations, memberships, roles, scoped resources, and assignments.
- `payments/` and `subscriptions/` — checkout, payment verification, fulfillment, plans, access, and entitlements.
- `quiz/` — practice, exams, questions, tracks, grading, learning dashboard, and custom platform administration.
- `templates/` and `static/` — Django templates and the shared frontend assets.

The installed project apps are `quiz`, `courses`, `accounts`, `pages`, `organizations`, `subscriptions`, and `payments`.

## Working safely

Before any code change, inspect the relevant implementation, related models/services/templates, and existing tests. Preserve established behavior unless the task explicitly changes it.

- Never reset the repository, discard user changes, or switch branches unless explicitly asked.
- Treat `.env`, credentials, payment settings, secret keys, and tokens as private. Never read values unnecessarily or add them to source, docs, assets, screenshots, or Git.
- Do not restore, delete, or otherwise alter `.env.example` automatically. Its deletion may be a user change.
- Do not install dependencies, recreate the virtual environment, change Git configuration, or alter database settings without explicit approval.
- Do not make unrelated refactors while fixing a feature or regression.

Before committing, inspect `git status --short`, `git diff --stat`, and `git diff`. Confirm every changed file is in scope and contains no secrets. Do not commit unless explicitly requested.

## Development workflow

For every feature or bugfix:

1. Understand the requirement and inspect the existing flow end-to-end.
2. Identify affected backend, frontend, authorization, and test files.
3. Search for existing tests and regression risks.
4. Write a short implementation plan before changing behavior.
5. For a defect, add or update the smallest regression test first and confirm the intended failure when practical.
6. Make the smallest correct change; preserve existing service boundaries and business logic.
7. Run focused tests, related tests, `venv\\Scripts\\python.exe manage.py check`, and broader tests when practical.
8. Review the final diff and report actual command output. Never claim tests pass without evidence.

When a failure is unrelated, reproduce and document it, but do not widen the task into unrelated cleanup. When a change exposes a structural issue, stop and explain the architectural decision needed rather than silently redesigning the system.

## Backend and authorization rules

- Django backend authorization is authoritative; navigation visibility is never a security control.
- Keep organization data constrained by the active organization and existing permission helpers. Do not trust only URL, form, or frontend filtering for scope.
- Reuse service layers for access, allocation, answer persistence, grading, subscriptions, payment fulfillment, and assignments. Do not duplicate business logic in views, templates, or JavaScript.
- Keep Django Admin as a super-admin fallback. The custom platform and organization interfaces must use the same backend rules.
- For migrations, inspect models and existing migrations first. Explain destructive effects before running anything that could alter data.

## Frontend rules

Use the existing server-rendered Django stack. Do not add a frontend framework or build system without explicit approval.

- Reuse the student shell in `templates/layouts/student/` and the admin shell in `templates/layouts/admin/`.
- Build on shared CSS in `static/css/theme.css`, `base.css`, `layout.css`, `components.css`, and `responsive.css` before adding feature-specific styles.
- Reuse common patterns for navigation, headers, sidebars, buttons, forms, tables, filters, pagination, empty states, access-denied states, and responsive behavior.
- Keep pages keyboard-usable and responsive on desktop, tablet, and mobile.
- Do not create a page or control unless the backend exposes the corresponding capability.

## Critical exam behavior

The student exam flow is catalog → preview → start → questions → editable final review → submit → student dashboard → read-only answer review.

- Final review is editable before submission; attempts are locked after submission.
- The submit route must handle direct GET safely and must not grade an already submitted attempt again.
- Timer expiry must retain saved answers, submit and lock the attempt, and preserve result/review availability.
- A question's choice order must stay deterministic for the same `UserExam` and question across navigation and refresh.
- Preserve question order from `UserExam.question_order` and keep result/answer review read-only after submission.

## Verification commands

Use the existing virtual environment when it is available:

```powershell
.\\venv\\Scripts\\python.exe --version
.\\venv\\Scripts\\python.exe -m django --version
.\\venv\\Scripts\\python.exe manage.py check
.\\venv\\Scripts\\python.exe manage.py test <target>
```

Run tests that cover the changed behavior first, then the related suite. Report warnings and failures precisely.
