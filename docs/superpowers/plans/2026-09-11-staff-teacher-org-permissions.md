# Staff / Teacher Organization Permissions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Staff/Teacher members operate their organization by creating questions, exams, and courses, managing students, and assigning/revoking resources, while restricting edits/deletes of content to content they personally created.

**Architecture:** Keep organization authorization centralized in `organizations/permissions.py`. Reuse the existing organization-scoped admin views and assignment service, adding object-level creator checks for Staff/Teacher mutations and preserving Owner/Admin organization-wide mutation rights. Add `created_by` to `Exam` because exams currently do not record their creator.

**Tech Stack:** Django, Django ORM, Django TestCase, MySQL CI, GitHub Actions.

**Spec:** Approved Staff/Teacher organization permission design from the current conversation.

## Global Constraints

- Staff/Teacher access requires an active membership in the target organization.
- Staff/Teacher may create questions, exams, and courses.
- Staff/Teacher may edit/delete only questions, exams, and courses they personally created.
- Owner/Admin retain organization-wide content mutation rights.
- Staff/Teacher may add/remove students and assign/revoke organization resources.
- Staff/Teacher may not manage organization settings, billing, or Owner/Admin roles.
- Cross-organization object access must remain denied.
- Platform-owned resources may remain attachable where existing business rules permit.

---

### Task 1: Add regression tests for Staff/Teacher operational access

**Files:**
- Modify: `organizations/test_security_authorization.py`

**Interfaces:**
- Consumes: existing organization membership, `Course`, `Question`, `Exam`, and organization admin URLs.
- Produces: failing tests covering Staff/Teacher create access, creator-only mutation, student denial, and cross-organization protection.

- [ ] **Step 1: Write failing tests**

Add tests that authenticate a Staff/Teacher member and assert:
- Staff can GET question/exam/course management pages and create endpoints.
- Staff can POST a new question and the saved question has `created_by=staff`.
- Staff can POST a new exam and the saved exam has `created_by=staff`.
- Staff can POST a new course and the saved course has `created_by=staff`.
- Staff can edit/delete their own question, exam, and course.
- Staff receives 404/403 and cannot mutate another member's organization content.
- Student cannot access these operational endpoints.
- Staff can add/remove a student through the existing student endpoints.
- Staff can access assignment list/create/revoke endpoints while students cannot.

Use the repository's existing forms and URL names instead of bypassing views. For POST tests, provide the minimum valid form fields required by the current models/forms.

- [ ] **Step 2: Run the focused tests and verify RED**

Run the organization authorization test module in CI-compatible form. Expected failures should identify missing Staff authorization and missing `Exam.created_by`, not unrelated setup errors.

- [ ] **Step 3: Commit the failing tests**

```bash
git add organizations/test_security_authorization.py
git commit -m "test: cover staff teacher organization operations"
```

### Task 2: Add exam creator ownership tracking

**Files:**
- Modify: `quiz/models/exam.py`
- Create: `quiz/migrations/<next_migration>_exam_created_by.py`

**Interfaces:**
- Consumes: Django `AUTH_USER_MODEL`.
- Produces: nullable `Exam.created_by` relation with reverse name `exams_created`.

- [ ] **Step 1: Extend the failing tests to assert exam ownership**

The Staff exam-create test must assert the created exam records the authenticated creator.

- [ ] **Step 2: Run the focused test and verify RED**

Expected failure: `Exam` has no `created_by` field.

- [ ] **Step 3: Add the model field**

Add a nullable `SET_NULL` foreign key to `settings.AUTH_USER_MODEL`, matching the existing Question/Course ownership pattern:

```python
created_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="exams_created",
)
```

- [ ] **Step 4: Add the migration**

Create the next Quiz migration adding `created_by` to `Exam`, preserving existing rows by allowing null.

- [ ] **Step 5: Run the focused test and verify GREEN for ownership**

The exam creation test must now save the creator correctly.

- [ ] **Step 6: Commit**

```bash
git add quiz/models/exam.py quiz/migrations/<next_migration>.py
git commit -m "feat: track exam creator"
```

### Task 3: Add reusable creator-aware organization permission helpers

**Files:**
- Modify: `organizations/permissions.py`
- Modify: `organizations/test_security_authorization.py`

**Interfaces:**
- Consumes: active organization membership and model instances.
- Produces: a helper/decorator that allows Owner/Admin to mutate any organization resource and Staff/Teacher only their own resource.

- [ ] **Step 1: Add a focused failing authorization test**

Cover the exact policy boundary: Owner/Admin can mutate another user's organization content; Staff can mutate only content where `created_by_id == request.user.id`; Student is denied.

- [ ] **Step 2: Verify RED**

Run only the new authorization tests and confirm the Staff ownership case fails before the helper exists.

- [ ] **Step 3: Implement the minimal reusable authorization helper**

Provide an object-level check that first requires an active teaching membership, then permits all Owner/Admin members and permits Staff only when the resource creator matches the authenticated user. Keep the helper independent of any specific content model.

- [ ] **Step 4: Verify GREEN**

Run the focused authorization tests and confirm all role boundaries pass.

- [ ] **Step 5: Commit**

```bash
git add organizations/permissions.py organizations/test_security_authorization.py
git commit -m "feat: enforce staff creator ownership"
```

### Task 4: Update questions, exams, and courses views

**Files:**
- Modify: `organizations/views/admin/questions.py`
- Modify: `organizations/views/admin/exams.py`
- Modify: `organizations/views/admin/courses.py`
- Modify: `organizations/test_security_authorization.py`

**Interfaces:**
- Consumes: creator-aware authorization from Task 3 and existing forms.
- Produces: Staff/Teacher create access plus creator-only mutation, with Owner/Admin behavior unchanged.

- [ ] **Step 1: Verify RED for each view family**

Run the focused Staff question/exam/course endpoint tests. They must fail because the views currently require `org_admin_required` and exams do not record their creator.

- [ ] **Step 2: Change list/create access to teaching membership**

Use `org_teacher_required` for the organization content list and create endpoints. On creation, set `created_by=request.user` for Exam, as already done for Question and Course.

- [ ] **Step 3: Apply creator ownership to mutations**

For edit/delete/deactivate endpoints:
- Keep organization filtering in every lookup.
- Owner/Admin may mutate any organization-owned resource.
- Staff may mutate only resources created by themselves.
- Do not allow Staff to mutate platform-owned or another-organization resources through these URLs.
- Preserve existing publication/approval safeguards for exams and courses.

- [ ] **Step 4: Verify GREEN**

Run all content authorization tests, including own-resource success and another-creator denial.

- [ ] **Step 5: Commit**

```bash
git add organizations/views/admin/questions.py organizations/views/admin/exams.py organizations/views/admin/courses.py organizations/test_security_authorization.py
git commit -m "feat: enable staff content management"
```

### Task 5: Enable Staff/Teacher student management without role escalation

**Files:**
- Modify: `organizations/views/admin/students.py`
- Modify: `organizations/test_security_authorization.py`

**Interfaces:**
- Consumes: `org_teacher_required` and existing membership mutation rules.
- Produces: Staff can add/remove students and cannot create, promote, demote, or remove Owner/Admin memberships.

- [ ] **Step 1: Add failing Staff add/remove tests**

Authenticate as Staff and assert student add/remove succeeds within the same organization. Assert attempts to add Owner/Admin roles remain rejected.

- [ ] **Step 2: Verify RED**

The tests should fail because the endpoints currently require `org_admin_required`.

- [ ] **Step 3: Change add/list/remove authorization to teaching membership**

Use `org_teacher_required` for student listing, add, and remove. Keep role input restricted to Student/Staff and retain the existing guard preventing modification/removal of administrative memberships.

Do not expand Staff into organization settings or administrator-role management.

- [ ] **Step 4: Verify GREEN**

Run focused student authorization tests.

- [ ] **Step 5: Commit**

```bash
git add organizations/views/admin/students.py organizations/test_security_authorization.py
git commit -m "feat: allow staff student management"
```

### Task 6: Align assignment UI authorization and verify navigation

**Files:**
- Modify: `organizations/views/admin/assignments.py` only if tests expose a gap.
- Modify: relevant organization workspace/sidebar template only if the existing navigation does not expose the newly permitted operations.
- Modify: `organizations/test_security_authorization.py`

**Interfaces:**
- Consumes: existing assignment service, which already validates Staff/Teacher student-management capability.
- Produces: Staff/Teacher assignment list/create/revoke access without weakening organization or student boundaries.

- [ ] **Step 1: Add failing endpoint tests for Staff assignment operations**

Assert Staff can access assignment list/create/revoke for students/resources in their organization and Student cannot.

- [ ] **Step 2: Verify RED or confirm existing behavior**

If assignment tests already pass, do not change the service or views unnecessarily. Only change code if an endpoint-level gap is demonstrated.

- [ ] **Step 3: Update navigation only where needed**

Ensure the Staff workspace links to Questions, Exams, Courses, Students, and Assignments. Do not expose settings, billing, or administrative role management.

- [ ] **Step 4: Verify GREEN**

Run the focused endpoint tests and existing sidebar/workspace tests.

- [ ] **Step 5: Commit**

```bash
git add organizations/views organizations/templates organizations/test_security_authorization.py
git commit -m "test: verify staff assignment workspace access"
```

### Task 7: Full regression and CI verification

**Files:**
- Modify: only files required by verified test failures.

**Interfaces:**
- Consumes: all implementation changes from Tasks 1-6.
- Produces: verified organization authorization behavior on the feature branch.

- [ ] **Step 1: Run the complete organization test suite**

Run:

```bash
python manage.py test organizations -v 2
```

Expected: all organization tests pass with zero failures/errors.

- [ ] **Step 2: Run the complete project test suite if the repository CI exposes one**

Use the repository's documented test command and resolve only regressions caused by this feature.

- [ ] **Step 3: Push/verify GitHub Actions**

Confirm the organization CI workflow for the feature branch completes successfully.

- [ ] **Step 4: Review the final diff**

Confirm no changes grant Staff/Teacher access to billing, organization settings, Owner/Admin role management, cross-organization resources, or another teacher's content mutation.

- [ ] **Step 5: Commit any final verified fixes**

```bash
git add .
git commit -m "test: verify organization staff permissions"
```
