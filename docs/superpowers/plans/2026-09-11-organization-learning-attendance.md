# Organization Learning, Attendance & Results Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tenant-safe organization academic system covering student records, class enrollment, teacher scope, class/student learning assignments, attendance and device integration, notifications, published results, and derived progress dashboards.

**Architecture:** Keep `OrganizationMember` as organization identity/role and add organization-scoped academic records on top. Keep direct `ResourceAssignment`/`ResourceAccess` for individual learning access while adding class-targeted assignment resolution. Build attendance as an event-driven, device-agnostic domain with a management-command scheduler, and expose exam results through an explicit publication layer over the existing `UserExam` attempt model.

**Tech Stack:** Django 6.0, Python 3.12, MySQL 8.0, existing Django templates/services/tests, Django email backend, provider-neutral SMS adapter, Django management commands for scheduled processing.

**Spec:** `docs/superpowers/specs/2026-09-11-organization-learning-attendance-design.md`

## Global Constraints

- `Organization` is the tenant boundary; every academic/attendance/result query must be organization-scoped.
- `OrganizationMember` remains the role/identity record; do not put class enrollment history into membership.
- Staff/Teacher content mutation remains creator-owned as already implemented.
- Students may edit only their own explicitly self-service profile fields.
- Teachers are scoped by active `ClassTeacher` assignments.
- Class assignments must not materialize one duplicate assignment per student.
- `ResourceAccess` remains the final learning authorization boundary.
- Attendance device events must be idempotent and device-authenticated.
- Result publication is explicit; raw submitted attempts are not automatically visible to students.
- Progress percentages are derived, not manually editable.
- Do not add Celery/Redis as a mandatory dependency for this feature.
- Preserve existing routes and regression behavior unless a new route is required by this feature.
- Run targeted tests after every task and the full Django suite before merge.

---

### Task 1: Organization student and academic models

**Files:**
- Create: `organizations/models/student.py`
- Create: `organizations/models/academic.py`
- Modify: `organizations/models/__init__.py`
- Create: `organizations/migrations/<generated migration>`
- Test: `organizations/test_student_academic_models.py`

**Interfaces:**
- Produces `OrganizationStudent`, `Guardian`, `StudentGuardian`, `AcademicYear`, `OrganizationClass`, `ClassSection`, and `StudentEnrollment`.
- Later tasks consume these models through `student.enrollments`, `class_section.enrollments`, and organization-scoped querysets.

- [ ] **Step 1: Write failing model tests**

```python
class StudentAcademicModelTests(TestCase):
    def test_student_identity_is_unique_per_organization(self):
        # Create the same user in two organizations successfully,
        # but reject a duplicate student record in one organization.
        ...

    def test_active_enrollment_is_unique_for_an_academic_year(self):
        ...

    def test_class_section_and_student_must_share_organization(self):
        ...

    def test_historical_enrollment_can_be_retained_after_transfer(self):
        ...
```

The test suite must use actual Django ORM objects and assert `ValidationError`/`IntegrityError` according to the implemented constraint strategy.

- [ ] **Step 2: Run targeted tests and verify failure**

Run:

```bash
python manage.py test organizations.test_student_academic_models -v 2
```

Expected: FAIL because the new models do not exist yet.

- [ ] **Step 3: Implement models**

Use foreign keys to `AUTH_USER_MODEL` and `Organization`. Enforce organization consistency in `clean()` and service-layer operations. Use conditional/transaction-safe logic where MySQL cannot express a partial unique constraint. `StudentEnrollment` must retain completed/transferred rows and allow only one active enrollment per student/year.

- [ ] **Step 4: Generate migration**

Run:

```bash
python manage.py makemigrations organizations
python manage.py migrate --plan
```

Do not delete or rewrite existing organization migrations.

- [ ] **Step 5: Run tests**

```bash
python manage.py test organizations.test_student_academic_models -v 2
```

- [ ] **Step 6: Commit**

```bash
git add organizations/models organizations/migrations organizations/test_student_academic_models.py
git commit -m "feat: add organization student academic models"
```

---

### Task 2: Guardian management and student self-service profile

**Files:**
- Modify: `organizations/models/student.py`
- Create: `organizations/forms/student.py`
- Create: `organizations/services/students.py`
- Create: `organizations/views/student_profile.py`
- Modify: `organizations/urls.py`
- Create: `templates/organizations/student/profile.html`
- Create: `templates/organizations/student/profile_edit.html`
- Test: `organizations/test_student_profile.py`

**Interfaces:**
- Produces service functions `get_organization_student(user, organization)`, `update_student_profile(*, actor, organization, student, data)`, and guardian-management helpers.
- Produces student routes under the existing organization namespace without accepting a user ID as the ownership source for self-service.

- [ ] **Step 1: Write failing permission/profile tests**

```python
def test_student_can_view_and_update_own_profile(self):
    ...

def test_student_cannot_update_enrollment_or_student_id(self):
    ...

def test_admin_can_view_and_edit_student_profile(self):
    ...

def test_teacher_can_view_only_students_in_assigned_class(self):
    ...

def test_student_cannot_view_profile_from_another_organization(self):
    ...
```

- [ ] **Step 2: Run tests and verify failure**

```bash
python manage.py test organizations.test_student_profile -v 2
```

Expected: FAIL because the service/forms/views are absent.

- [ ] **Step 3: Implement service and form boundaries**

The student form must whitelist only self-service fields such as name/contact/guardian contact fields that are explicitly designated editable. `student_id`, admission number, status, organization, enrollment, class, section and roll number must be excluded from the student form and rejected if supplied to the service.

- [ ] **Step 4: Implement views/templates and routes**

Use `org_student_required` plus an `OrganizationStudent` existence check for student self-service. Admin uses `org_admin_required`. Teacher profile access must call a service that checks `ClassTeacher` scope.

- [ ] **Step 5: Run tests**

```bash
python manage.py test organizations.test_student_profile -v 2
```

- [ ] **Step 6: Commit**

```bash
git add organizations/forms organizations/services organizations/views organizations/urls.py templates/organizations/student organizations/test_student_profile.py
 git commit -m "feat: add organization student profile portal"
```

---

### Task 3: Teacher-class management and enrollment workflows

**Files:**
- Create: `organizations/services/enrollment.py`
- Create: `organizations/views/admin/academic.py`
- Modify: `organizations/urls.py`
- Modify: `templates/organizations/admin/base.html`
- Create: `templates/organizations/admin/academic/*.html`
- Test: `organizations/test_academic_permissions.py`

**Interfaces:**
- Produces `enroll_student(*, actor, student, section, roll_number=None)`, `transfer_student(*, actor, enrollment, section, roll_number=None)`, and `assign_teacher_to_section(*, actor, teacher, section, academic_year, subject=None)`.
- Later assignment and attendance services use active enrollments and class-teacher scope.

- [ ] **Step 1: Write failing authorization tests**

```python
def test_admin_can_enroll_existing_organization_student(self):
    ...

def test_teacher_can_enroll_student_only_into_assigned_section(self):
    ...

def test_teacher_cannot_move_student_between_unassigned_sections(self):
    ...

def test_teacher_cannot_enroll_platform_user_without_organization_student_record(self):
    ...

def test_cross_organization_enrollment_is_denied(self):
    ...
```

- [ ] **Step 2: Run tests and verify failure**

```bash
python manage.py test organizations.test_academic_permissions -v 2
```

- [ ] **Step 3: Implement enrollment service**

The service must require an `OrganizationStudent`, an organization-matching section and an active actor membership. Teacher actions must resolve `ClassTeacher` assignments before mutation. Owner/Admin can manage organization-wide academic placement.

- [ ] **Step 4: Add admin academic screens**

Provide academic-year, class, section, student enrollment and teacher assignment screens. Staff should see only assigned classes and students. Owner/Admin should see organization-wide academic data.

- [ ] **Step 5: Run tests**

```bash
python manage.py test organizations.test_academic_permissions -v 2
```

- [ ] **Step 6: Commit**

```bash
git add organizations/services/enrollment.py organizations/views/admin/academic.py organizations/urls.py templates/organizations/admin organizations/test_academic_permissions.py
 git commit -m "feat: add academic enrollment and teacher class scope"
```

---

### Task 4: Class-targeted course/track/exam assignments

**Files:**
- Create: `organizations/models/class_assignment.py`
- Create: `organizations/services/class_assignments.py`
- Modify: `organizations/services/assignments.py`
- Modify: the existing access service that implements final `ResourceAccess` checks
- Modify: `organizations/views/admin/assignments.py`
- Modify: `organizations/urls.py`
- Test: `organizations/test_class_assignments.py`

**Interfaces:**
- Produces `ClassResourceAssignment` and `assign_class_resource(*, actor, section, resource_type, resource_id, ...)`.
- Effective-access helper must answer `student_can_access_resource(student, organization, resource)` using direct assignment OR active class assignment through current enrollment.

- [ ] **Step 1: Write failing tests**

```python
def test_teacher_can_assign_course_to_assigned_class(self):
    ...

def test_teacher_cannot_assign_resource_to_unassigned_class(self):
    ...

def test_enrolled_student_inherits_class_resource_access(self):
    ...

def test_student_transferred_out_of_class_loses_class_assignment_access(self):
    ...

def test_direct_assignment_still_works(self):
    ...
```

- [ ] **Step 2: Run targeted tests**

```bash
python manage.py test organizations.test_class_assignments -v 2
```

Expected: FAIL.

- [ ] **Step 3: Implement class assignment model/service**

Store one class assignment per class/resource. Validate organization, active section, resource ownership/availability and teacher scope. Preserve existing direct `ResourceAssignment` behavior.

- [ ] **Step 4: Integrate final access resolution**

Before granting organization learning access, resolve current enrollment and active class assignments. Do not create duplicate `ResourceAccess` rows for every class member.

- [ ] **Step 5: Add UI and run tests**

```bash
python manage.py test organizations.test_class_assignments organizations.test_security_authorization -v 2
```

- [ ] **Step 6: Commit**

```bash
git add organizations/models/class_assignment.py organizations/services organizations/views/admin/assignments.py organizations/urls.py organizations/test_class_assignments.py
 git commit -m "feat: support class learning assignments"
```

---

### Task 5: Attendance domain and manual attendance

**Files:**
- Create: `organizations/models/attendance.py`
- Create: `organizations/services/attendance.py`
- Create: `organizations/views/admin/attendance.py`
- Modify: `organizations/urls.py`
- Modify: `templates/organizations/admin/base.html`
- Create: `templates/organizations/admin/attendance/*.html`
- Test: `organizations/test_attendance.py`

**Interfaces:**
- Produces `AttendanceRule`, `AttendanceRecord`, `AttendanceDevice`, `StudentAttendanceIdentifier`, and immutable `AttendanceEvent`.
- Produces `record_attendance_event(...)`, `mark_manual_attendance(...)`, `finalize_absences(...)`, and `get_student_attendance_summary(...)`.

- [ ] **Step 1: Write failing tests**

```python
def test_manual_present_record_is_created_for_current_enrollment(self):
    ...

def test_duplicate_daily_checkins_do_not_create_duplicate_records(self):
    ...

def test_late_status_uses_organization_rule(self):
    ...

def test_absence_finalization_marks_missing_enrolled_students_absent(self):
    ...

def test_manual_correction_is_audited(self):
    ...
```

- [ ] **Step 2: Run tests and verify failure**

```bash
python manage.py test organizations.test_attendance -v 2
```

- [ ] **Step 3: Implement attendance models/services**

`AttendanceEvent` is immutable after creation. `AttendanceRecord` is unique by organization + enrollment + date. Device/manual source and actor are retained. Attendance rules determine late and absence-finalization behavior.

- [ ] **Step 4: Add manual attendance screens**

Teachers can mark attendance only for assigned classes. Admins can manage organization-wide attendance. Students can view only their own attendance.

- [ ] **Step 5: Run tests**

```bash
python manage.py test organizations.test_attendance -v 2
```

- [ ] **Step 6: Commit**

```bash
git add organizations/models/attendance.py organizations/services/attendance.py organizations/views/admin/attendance.py organizations/urls.py templates/organizations/admin organizations/test_attendance.py
 git commit -m "feat: add organization attendance"
```

---

### Task 6: Device ingestion adapter and scheduled absence processing

**Files:**
- Create: `organizations/services/attendance_devices.py`
- Create: `organizations/views/attendance_api.py`
- Create: `organizations/management/commands/finalize_attendance.py`
- Modify: `organizations/urls.py`
- Test: `organizations/test_attendance_devices.py`
- Test: `organizations/test_attendance_commands.py`

**Interfaces:**
- Produces an authenticated device ingestion endpoint and provider-neutral adapter interface.
- `ingest_device_event(*, device, external_event_id, identifier, event_timestamp, payload)` must be idempotent.
- `finalize_attendance` management command must process only eligible active enrollments.

- [ ] **Step 1: Write failing device tests**

```python
def test_device_event_requires_authenticated_registered_device(self):
    ...

def test_device_event_resolves_student_identifier_to_current_enrollment(self):
    ...

def test_duplicate_external_event_is_processed_once(self):
    ...

def test_device_cannot_submit_for_another_organization(self):
    ...

def test_finalize_attendance_command_is_idempotent(self):
    ...
```

- [ ] **Step 2: Run tests and verify failure**

```bash
python manage.py test organizations.test_attendance_devices organizations.test_attendance_commands -v 2
```

- [ ] **Step 3: Implement ingestion**

Authenticate the device using a deployment-managed credential/API key. Never trust organization ID from an unauthenticated request. Store the raw event first, then process it through the attendance service. A duplicate `external_event_id` for the same device must return the existing event/result without a second attendance mutation.

- [ ] **Step 4: Implement command**

Provide:

```bash
python manage.py finalize_attendance --date 2026-09-11
```

The command must be safe to rerun. Deployment scheduling can use cron/JAMS without introducing a new mandatory worker framework.

- [ ] **Step 5: Run tests**

```bash
python manage.py test organizations.test_attendance_devices organizations.test_attendance_commands -v 2
```

- [ ] **Step 6: Commit**

```bash
git add organizations/services/attendance_devices.py organizations/views/attendance_api.py organizations/management/commands/finalize_attendance.py organizations/urls.py organizations/test_attendance_devices.py organizations/test_attendance_commands.py
 git commit -m "feat: add attendance device ingestion"
```

---

### Task 7: Email/SMS notification infrastructure

**Files:**
- Create: `organizations/models/notification_delivery.py`
- Create: `organizations/services/notifications.py`
- Create: `organizations/services/sms.py`
- Create: `organizations/management/commands/send_attendance_notifications.py`
- Create: `templates/email/attendance_absence.txt`
- Test: `organizations/test_attendance_notifications.py`

**Interfaces:**
- Produces `send_notification(...)` and `send_attendance_notifications(...)`.
- SMS provider interface is `send_sms(*, to, message, idempotency_key)`; the default implementation may be a configured HTTP adapter without adding a provider SDK.

- [ ] **Step 1: Write failing tests**

```python
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
def test_absence_sends_email_to_primary_guardian(self):
    ...

def test_absence_notifies_assigned_teacher(self):
    ...

def test_notification_is_not_sent_twice_for_same_event_channel_recipient(self):
    ...

def test_sms_provider_failure_is_recorded_without_losing_attendance_record(self):
    ...
```

- [ ] **Step 2: Run tests and verify failure**

```bash
python manage.py test organizations.test_attendance_notifications -v 2
```

- [ ] **Step 3: Implement notification delivery model/service**

Record recipient, channel, event type, status, attempts and provider reference. Email uses Django's configured backend. SMS uses a provider adapter and deployment configuration. Do not store provider secrets in database records.

- [ ] **Step 4: Add attendance notification command**

```bash
python manage.py send_attendance_notifications --date 2026-09-11
```

The command must be idempotent and safe for scheduled execution.

- [ ] **Step 5: Run tests**

```bash
python manage.py test organizations.test_attendance_notifications -v 2
```

- [ ] **Step 6: Commit**

```bash
git add organizations/models/notification_delivery.py organizations/services/notifications.py organizations/services/sms.py organizations/management/commands/send_attendance_notifications.py templates/email organizations/test_attendance_notifications.py
 git commit -m "feat: add attendance notifications"
```

---

### Task 8: Result publication over existing exam attempts

**Files:**
- Create: `quiz/models/result.py`
- Modify: `quiz/models/__init__.py`
- Create: `quiz/migrations/<generated migration>`
- Create: `quiz/services/results.py`
- Create/modify: `organizations/views/admin/results.py`
- Modify: `organizations/urls.py`
- Create: `templates/organizations/admin/results/*.html`
- Modify: student portal views/templates
- Test: `quiz/tests/test_result_publication.py`

**Interfaces:**
- Produces `ResultRecord` with pending/published/hidden states.
- Produces `publish_result(*, actor, result)`, `hide_result(*, actor, result)`, and `get_published_results(*, student, organization)`.
- Uses existing `UserExam` attempts as the source attempt record rather than creating a second exam-attempt engine.

- [ ] **Step 1: Write failing tests**

```python
def test_submitted_attempt_creates_or_updates_pending_result(self):
    ...

def test_student_cannot_see_pending_result(self):
    ...

def test_student_can_see_published_result(self):
    ...

def test_teacher_can_manage_results_only_for_assigned_students(self):
    ...

def test_result_publication_is_audited(self):
    ...
```

- [ ] **Step 2: Run tests and verify failure**

```bash
python manage.py test quiz.tests.test_result_publication -v 2
```

- [ ] **Step 3: Implement result model/service**

Copy the evaluated score/percentage/pass state from the submitted `UserExam` into the organization result record at evaluation time. Publication is a separate transaction and records actor/time. A student query must filter `publication_status="published"` and the logged-in student's organization enrollment.

- [ ] **Step 4: Add teacher/admin result UI**

Teachers see only authorized class/student results. Owner/Admin see organization-wide results and publication controls. Students see only published results.

- [ ] **Step 5: Run tests**

```bash
python manage.py test quiz.tests.test_result_publication organizations.test_security_authorization -v 2
```

- [ ] **Step 6: Commit**

```bash
git add quiz/models quiz/migrations quiz/services organizations/views/admin/results.py organizations/urls.py templates/organizations/admin/results templates/organizations/student quiz/tests/test_result_publication.py
 git commit -m "feat: add organization result publication"
```

---

### Task 9: Derived progress service and dashboards

**Files:**
- Create: `organizations/services/progress.py`
- Modify: `organizations/services/dashboard/overview.py`
- Modify: `organizations/views/student_portal.py`
- Modify: `organizations/views/member_portal.py`
- Create: `organizations/views/progress.py`
- Create/modify: student/teacher/admin dashboard templates
- Test: `organizations/test_progress.py`

**Interfaces:**
- Produces `get_student_progress(*, student, organization)`, `get_class_progress(*, section, actor)`, and `get_organization_progress(*, organization, actor)`.
- Returns derived metrics: attendance rate, assignment completion, exam average/pass rate, course progress where supported, track progress where supported, and overall progress.

- [ ] **Step 1: Write failing tests**

```python
def test_student_progress_combines_attendance_assignments_and_published_results(self):
    ...

def test_hidden_results_do_not_affect_published_exam_progress(self):
    ...

def test_teacher_progress_is_limited_to_assigned_class(self):
    ...

def test_student_progress_does_not_include_another_organization(self):
    ...

def test_progress_service_uses_bulk_queries_for_class_dashboard(self):
    ...
```

- [ ] **Step 2: Run tests and verify failure**

```bash
python manage.py test organizations.test_progress -v 2
```

- [ ] **Step 3: Implement derived progress service**

Compute metrics from existing records rather than storing a manually editable percentage. Use `select_related`, `prefetch_related`, grouped aggregates and bulk queries for class/admin dashboards. Keep the weighting rules explicit in one service module.

- [ ] **Step 4: Add dashboard presentation**

Student dashboard sections: attendance, courses/tracks, exams/results and progress. Teacher dashboard: class attendance and student progress. Admin dashboard: organization attendance, learning completion, exam performance and pending results.

- [ ] **Step 5: Run tests**

```bash
python manage.py test organizations.test_progress -v 2
```

- [ ] **Step 6: Commit**

```bash
git add organizations/services/progress.py organizations/services/dashboard/overview.py organizations/views organizations/test_progress.py templates
 git commit -m "feat: add student and class progress dashboards"
```

---

### Task 10: Navigation, admin registration and security regression suite

**Files:**
- Modify: `organizations/admin.py`
- Modify: `organizations/models/__init__.py`
- Modify: `templates/organizations/admin/base.html`
- Modify: `templates/organizations/member/workspace.html`
- Test: `organizations/test_security_authorization.py`
- Test: `organizations/test_sidebar_navigation.py`
- Test: `organizations/test_academic_permissions.py`

- [ ] **Step 1: Add regression cases**

```python
def test_student_cannot_open_admin_academic_pages(self):
    ...

def test_staff_cannot_change_roles_or_organization_settings(self):
    ...

def test_teacher_cannot_access_another_class_student_attendance(self):
    ...

def test_cross_organization_device_and_result_access_is_denied(self):
    ...
```

- [ ] **Step 2: Register models and update navigation**

Expose academic, attendance, results and relevant student-management pages according to role. UI hiding is supplementary; server-side decorators/services remain authoritative.

- [ ] **Step 3: Run focused security tests**

```bash
python manage.py test organizations.test_security_authorization organizations.test_academic_permissions organizations.test_attendance organizations.test_class_assignments -v 2
```

- [ ] **Step 4: Run full test suite**

```bash
python manage.py test --noinput -v 2
```

The repository's full-test workflow uses the same command with MySQL 8.0 and Python 3.12, so this is the local acceptance command.

- [ ] **Step 5: Commit**

```bash
git add organizations/admin.py organizations/models/__init__.py templates organizations/test_security_authorization.py organizations/test_sidebar_navigation.py
 git commit -m "test: harden organization academic permissions"
```

---

## Verification and rollout

- [ ] Verify `python manage.py check` succeeds.
- [ ] Verify all new migrations apply cleanly from the current main migration state.
- [ ] Verify targeted model/security/attendance/result/progress tests pass.
- [ ] Verify `python manage.py test --noinput -v 2` passes locally.
- [ ] Push the feature branch and inspect organization/full CI.
- [ ] Review changed files and PR comments before merge.
- [ ] Do not claim the feature is complete until the verification command and CI results are actually successful.
- [ ] Merge into `main` only after verification; this repo's current workflow runs the full test suite on pushes to `main` and pull requests.
