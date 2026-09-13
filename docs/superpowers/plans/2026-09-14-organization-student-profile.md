# Organization Student Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically provision an organization-specific student profile when a student is added and expose a secure profile workflow for students.

**Architecture:** Reuse the existing `OrganizationStudent` model as the organization-scoped profile keyed by organization and user. Keep organization-specific student/guardian data on that record, use the existing global `UserProfile.phone` for the account contact number, provision the student record idempotently from membership creation, and expose the profile through student-facing organization navigation.

**Tech Stack:** Django models, ModelForms, server-rendered templates, Django TestCase.

**Spec:** `docs/specs/organization-student-profile.md`

## Global Constraints

- Organization membership is the authorization boundary.
- The same user may belong to multiple organizations with independent student profiles.
- Enrollment and administrative fields remain organization-controlled.
- Students can edit only their own profile.
- Teachers can view but not edit student profiles.
- No cross-organization profile access is permitted.

---

### Task 1: Confirm and reuse profile data model

**Files:**
- Reuse: `organizations/models/student.py`
- Reuse: `accounts/models/profile.py`
- Test: `organizations/test_student_profile.py`

- [ ] Reuse the existing `OrganizationStudent` fields for name, DOB, guardian name, guardian phone, and address.
- [ ] Use the existing account `UserProfile.phone` for student contact number rather than introducing duplicate phone storage.
- [ ] Keep the existing `(organization, user)` uniqueness boundary.

### Task 2: Update profile form and service

**Files:**
- Modify: `organizations/forms/student.py`
- Modify: `organizations/services/students.py`
- Test: `organizations/test_student_profile.py`

- [ ] Add contact phone to the profile form.
- [ ] Update the service to save contact phone through `UserProfile`.
- [ ] Preserve administrative/enrollment protections.
- [ ] Add tests for student self-edit and forbidden administrative edits.

### Task 3: Provision profiles when students are added

**Files:**
- Modify: `organizations/views/admin/students.py`
- Test: `organizations/test_student_profile.py`

- [ ] Create `OrganizationStudent` with `get_or_create` whenever a membership is created or activated as a student.
- [ ] Make provisioning idempotent for existing profiles.
- [ ] Cover both a new student membership and an existing membership changed to student.

### Task 4: Surface the profile in the student account

**Files:**
- Modify: `templates/organizations/member/workspace.html`
- Modify: `templates/organizations/student/profile.html`
- Modify: `templates/organizations/student/profile_edit.html`
- Test: `organizations/test_student_profile.py`

- [ ] Add a student-only `My Profile` entry in the organization workspace.
- [ ] Keep profile pages organization-branded and clearly scoped.
- [ ] Display contact and guardian information.
- [ ] Keep admin/teacher views separate from student editing controls.

### Task 5: Verify

- [ ] Run the focused student profile test suite.
- [ ] Run the organization test suite.
- [ ] Inspect GitHub Actions for the resulting commit.
- [ ] Report any unavailable or failing verification honestly.
