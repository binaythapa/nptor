# Staff / Teacher Organization Permissions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Staff/Teacher members operate their organization by creating questions, exams, and courses, managing students, and assigning/revoking resources, while restricting edits/deletes of content to content they personally created.

**Architecture:** Keep role and membership authorization centralized in `organizations/permissions.py`. Put the reusable content-ownership rule in `organizations/services/content_permissions.py` so it can remain generic while staying close to resource business rules. Reuse the existing organization-scoped admin views and assignment service, preserving Owner/Admin organization-wide mutation rights.

**Tech Stack:** Django, Django ORM, Django TestCase, MySQL CI, GitHub Actions.

**Spec:** Approved Staff/Teacher organization permission design from the current conversation.

## Global Constraints

- Staff/Teacher access requires an active membership in the target organization.
- Staff/Teacher may create questions, exams, and courses.
- Staff/Teacher may edit/delete only questions, exams, and courses they personally created.
- Owner/Admin retain organization-wide content mutation rights.
- Staff/Teacher may add/remove students and assign/revoke organization resources.
- Staff/Teacher may not manage organization settings, billing, or Owner/Admin roles.
- Staff/Teacher may not add, remove, promote, or demote other Staff/Teacher members.
- Cross-organization object access must remain denied.
- Platform-owned resources may remain attachable where existing business rules permit.

---

### Task 1: Add regression tests for Staff/Teacher operational access

**Files:**
- Modify: `organizations/test_security_authorization.py`
- Create: `organizations/test_staff_content_creation.py`

**Interfaces:**
- Consumes: existing organization membership, content models, forms, and organization admin URLs.
- Produces: tests covering Staff/Teacher page access, creator-only mutation, student management, and content creation ownership.

- [x] **Step 1: Write failing tests**

Added Staff/Teacher endpoint, ownership, deletion, student-management, and content-creation tests before the corresponding implementation was complete.

- [x] **Step 2: Verify the tests target the intended boundaries**

The tests assert active organization membership, Staff/Teacher access, creator ownership, Student denial, and protection against Staff role escalation.

### Task 2: Add exam creator ownership tracking

**Files:**
- Modify: `quiz/models/exam.py`
- Create: `quiz/migrations/0010_exam_created_by.py`

**Interfaces:**
- Consumes: Django `AUTH_USER_MODEL`.
- Produces: nullable `Exam.created_by` relation with reverse name `exams_created`.

- [x] **Step 1: Add the model field**

Added a nullable `SET_NULL` foreign key to the authenticated user model.

- [x] **Step 2: Add the migration**

Added `quiz/migrations/0010_exam_created_by.py`, depending on `0009_mysql_safe_active_uniqueness`.

- [x] **Step 3: Record the creator during organization exam creation**

The organization exam-create view sets `exam.created_by = request.user` before saving.

### Task 3: Add creator-aware content authorization

**Files:**
- Create: `organizations/services/content_permissions.py`
- Modify: `organizations/test_security_authorization.py`

**Interfaces:**
- Consumes: active organization membership and a resource with `organization_id` and optional `created_by_id`.
- Produces: `user_can_manage_owned_content(user, organization, resource)`.

- [x] **Step 1: Define the policy test**

Staff may mutate only their own organization content; Owner/Admin may mutate organization content regardless of creator; Students and cross-organization resources are denied.

- [x] **Step 2: Implement the minimal helper**

The helper requires an active membership, requires the resource organization to match, grants Owner/Admin access, and otherwise grants only Staff access where `created_by_id` matches the actor.

### Task 4: Enable Staff/Teacher content management

**Files:**
- Modify: `organizations/views/admin/questions.py`
- Modify: `organizations/views/admin/exams.py`
- Modify: `organizations/views/admin/courses.py`
- Modify: `organizations/test_security_authorization.py`
- Modify: `organizations/test_staff_content_creation.py`

**Interfaces:**
- Consumes: `org_teacher_required`, `user_can_manage_owned_content`, and existing forms.
- Produces: Staff/Teacher create/list access plus creator-only edit/delete/deactivate access.

- [x] **Step 1: Enable teaching-role access to content pages**

Question and exam list/create views and course CRUD list/create views use `org_teacher_required`.

- [x] **Step 2: Enforce creator ownership on mutations**

Question, exam, and course edit/delete/deactivate paths retain organization-scoped lookups and call `user_can_manage_owned_content` before mutation.

- [x] **Step 3: Scope Staff content lists**

Staff/Teacher question and exam lists are limited to content they created. Course CRUD remains organization-scoped while mutation authorization is creator-scoped.

- [x] **Step 4: Preserve existing publication/approval controls**

Published exams remain immutable through these organization mutation paths, and courses remain mutable only in their existing draft/changes/rejected states.

### Task 5: Enable Staff/Teacher student management without role escalation

**Files:**
- Modify: `organizations/views/admin/students.py`
- Modify: `organizations/test_security_authorization.py`

**Interfaces:**
- Consumes: `org_teacher_required` and existing membership/access cleanup behavior.
- Produces: Staff/Teacher student list/add/remove access without Staff role administration.

- [x] **Step 1: Enable teaching-role access to student list/add/remove**

Student list, add, and remove views use `org_teacher_required`.

- [x] **Step 2: Keep role administration restricted**

Role update remains Owner/Admin-only. Staff may add students only and may remove students only; they cannot create or change Staff memberships.

### Task 6: Preserve assignment authorization and update navigation

**Files:**
- Modify: `templates/organizations/member/workspace.html`
- Modify: `templates/organizations/admin/base.html`
- Modify: `organizations/test_security_authorization.py`

**Interfaces:**
- Consumes: existing assignment service and teaching-role views.
- Produces: Staff/Teacher workspace links to courses, questions, exams, students, and assignments without exposing administrator-only navigation.

- [x] **Step 1: Verify assignment endpoints**

Existing assignment views already use `org_teacher_required`, and the assignment service already validates Staff/Teacher student-management capability.

- [x] **Step 2: Add Staff/Teacher workspace operation links**

The member workspace exposes Courses, Questions, Exams, Students, and Assignments.

- [x] **Step 3: Scope admin navigation by role**

Staff/Teacher see operational navigation only. Dashboard, tracks, domains, categories, portfolio, and settings remain administrator-only.

### Task 7: Regression and CI verification

**Files:**
- Modify: only files required by verified test failures.

**Interfaces:**
- Consumes: implementation from Tasks 1-6.
- Produces: verified organization authorization behavior on the feature branch.

- [ ] **Step 1: Run the complete organization test suite**

Run:

```bash
python manage.py test organizations -v 2
```

Expected: all organization tests pass with zero failures/errors.

- [ ] **Step 2: Verify the complete project test suite**

Use the repository's existing full-test workflow and resolve only regressions caused by this feature.

- [ ] **Step 3: Review the final diff**

Confirm Staff/Teacher cannot mutate another teacher's content, manage administrator roles, access organization settings/billing, or cross organization boundaries.

- [ ] **Step 4: Verify GitHub Actions**

Confirm the organization test workflow and full test suite complete successfully for the final feature-branch commit.
