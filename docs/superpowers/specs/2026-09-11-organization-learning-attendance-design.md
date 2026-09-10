# Organization Learning, Attendance & Results Design

## Goal
Extend NPTOR from organization membership/content management into a tenant-safe academic management system covering organization students, classes, enrollment, parent/guardian relationships, class and student learning assignments, attendance/device integration, notifications, exam result publishing, and derived learning progress.

## Existing architecture to preserve
- `Organization` remains the tenant boundary.
- `OrganizationMember` remains the organization identity/role record; academic enrollment is separate.
- Existing organization permission decorators remain the authorization boundary.
- Staff/Teacher content mutation remains limited to content they created; Owner/Admin can manage organization-owned content.
- Existing `ResourceAssignment` and `ResourceAccess` remain valid for direct student learning access.
- Existing `Exam` and `UserExam` remain the exam definition/attempt foundation. `UserExam` already stores started/submitted/expired status, score and pass state.
- Existing `OrganizationAuditLog` is reused for academic, attendance and administrative audit events.
- Existing MySQL 8 / Django 6 / Python 3.12 test environment remains supported.

## Core domain model

### OrganizationStudent
Represents the fact that a student belongs to an organization. It is distinct from `OrganizationMember` so academic records do not become organization-role fields.

Fields:
- organization
- user
- student_id (organization-wide identifier)
- admission_number (optional)
- date_of_birth (optional)
- guardian_name/legacy compatibility only where required; canonical guardian data lives in Guardian relationship records
- status: active, inactive, graduated, withdrawn
- joined_at / updated_at

Rules:
- organization + user is unique.
- organization + student_id is unique when student_id is present.
- a student record requires an active Student organization membership.
- deleting a membership does not silently destroy academic history.

### Guardian
Represents a parent/guardian contact and can be linked to one or more organization students.

Fields:
- organization
- user (optional for guardians who have platform accounts)
- name
- relationship
- email
- phone
- preferred notification channels
- is_primary
- is_active

`StudentGuardian` links a guardian to an `OrganizationStudent`, with relationship and notification preferences. Guardian data is organization-scoped.

### AcademicYear
Fields:
- organization
- name
- start_date
- end_date
- is_current
- timestamps

Only one current academic year is allowed per organization through service-level locking/validation compatible with MySQL.

### OrganizationClass
Fields:
- organization
- name (for example Grade 10)
- code
- description
- is_active

### ClassSection
Fields:
- organization
- academic_year
- class
- name (A/B/C)
- capacity (optional)
- is_active

A section belongs to exactly one organization's academic year and class.

### StudentEnrollment
Represents a student's placement in a section for an academic year and preserves history.

Fields:
- student
- academic_year
- class_section
- roll_number
- status: active, completed, transferred, withdrawn
- joined_at
- left_at

Rules:
- active enrollment must match the student's organization.
- class section and academic year must belong to the same organization.
- a student has at most one active section enrollment for an academic year.
- historical enrollments are retained.

### ClassTeacher
Connects an organization staff/teacher membership to a class section for an academic year.

Fields:
- organization
- teacher (User)
- class_section
- academic_year
- subject (optional)
- is_primary
- active dates/status

Only Staff/Teacher organization members can be assigned. Teacher visibility is restricted to their assigned classes.

## Learning assignment model

Existing direct `ResourceAssignment` continues to support student-targeted course/track/exam assignments.

Add a separate class-targeted assignment model rather than forcing a class assignment into hundreds of individual rows. A class assignment contains:
- organization
- class_section
- resource type
- course/track/exam
- assigned_by
- lifecycle dates/status
- audit timestamps

Effective student access is resolved as:
1. direct active student assignment, or
2. active class assignment for a student's current enrollment.

This avoids duplicating assignment rows while allowing individual exceptions. Existing `ResourceAccess` remains the final user/resource authorization boundary; class-assignment resolution must be incorporated into the access service before a student is allowed into a resource.

## Student self-service portal

An enrolled student can access the organization learning dashboard only when:
- the user is authenticated;
- the user has an active Student membership for the organization;
- an active `OrganizationStudent` record exists.

Dashboard sections:
- organization identity
- student profile
- class/section and academic year
- courses
- tracks
- exams
- results
- attendance
- progress

Students may edit only personal profile/contact fields explicitly marked self-service. They cannot edit role, organization, student ID, admission number, enrollment, class, section, roll number, attendance, assignments, marks or results.

Owner/Admin can view and edit organization student profiles. Assigned teachers can view permitted student profile information but cannot edit protected enrollment/administrative fields.

## Attendance model

### AttendanceDevice
A classroom/device registration record:
- organization
- class_section (optional for portable/shared devices)
- name
- device_identifier
- device_type
- integration_mode: webhook, REST, polling, TCP/IP, CSV, manual
- endpoint/config metadata without secrets
- status
- last_seen_at
- timestamps

Device credentials/secrets must not be stored in plaintext in ordinary model fields. The integration service should accept configured credentials through the deployment secret/config mechanism.

### StudentAttendanceIdentifier
Maps a device identifier to an organization student:
- organization_student
- device
- identifier_type
- identifier_value
- is_active
- timestamps

Identifiers may represent RFID/NFC, biometric, QR or vendor-specific IDs.

### AttendanceRule
Organization/class configurable rules:
- expected start time
- late threshold
- absence finalization time
- whether duplicate scans update the first/last check-in
- enabled status

### AttendanceRecord
One daily attendance state per enrolled student/section/date:
- organization
- student
- enrollment
- attendance_date
- status: present, late, absent, excused, half_day, leave
- check_in_at
- check_out_at (optional)
- source: device, teacher, admin, import
- device (optional)
- marked_by (optional)
- notes
- timestamps

The first valid device check-in establishes presence; later scans can update last activity without creating duplicate daily records. Manual corrections retain audit history.

### AttendanceEvent
Immutable raw integration event:
- organization
- device
- external_event_id
- identifier
- event_timestamp
- received_at
- payload metadata
- processing status/error

A unique organization/device/external-event key makes device retries idempotent.

## Attendance workflow

1. Device sends/publishes a check-in event.
2. NPTOR authenticates the device and validates organization/device identity.
3. Identifier resolves to an active organization student.
4. Current enrollment resolves the class/section.
5. Attendance service creates/updates the day's attendance record.
6. The event is audited.
7. At the configured absence-finalization time, enrolled students without qualifying attendance are marked absent unless they have approved leave/excused status.
8. Notification service sends configured alerts to assigned teacher(s) and guardians.

Manual attendance remains available for classrooms without a connected device.

## Notifications

Create an organization-scoped notification delivery model and provider interface. Channels:
- email using Django's configured email backend;
- SMS through a provider adapter; no vendor-specific dependency in core attendance logic.

Notification records store recipient, channel, event type, status, provider message/reference ID when available, attempt count, timestamps and failure information.

Attendance notification policy is organization-configurable:
- absence to guardian;
- absence to assigned teacher;
- optional late notification;
- optional daily attendance summary.

Delivery must be idempotent per event/recipient/channel so device retries do not generate duplicate SMS/email.

The initial scheduled absence processor should be a Django management command suitable for cron/JAMS/server scheduling. The design must not require Celery as a new mandatory dependency.

## Exams and results

Reuse `Exam` as the exam definition and `UserExam` as the attempt record. Add an organization result publication layer rather than exposing raw attempt state directly.

### ResultRecord
A normalized evaluated result tied to:
- organization
- student
- exam
- user_exam attempt
- score
- percentage
- pass/fail
- evaluated_at
- evaluated_by
- publication status
- published_at
- published_by
- optional remarks

A student can see only their own published results. Teachers can view results for students in assigned classes and exams they are authorized to manage. Owner/Admin can manage all organization results.

Result publication states:
- pending
- published
- hidden

Publishing must be an explicit action. Hidden/pending results are not visible to students or guardians.

## Progress

Progress is derived from underlying activity and must not be a manually editable percentage.

Initial progress signals:
- course/resource completion where supported by the existing learning system;
- active/completed assignments;
- exam completion;
- published exam performance;
- attendance rate.

A progress service should calculate:
- overall progress;
- course progress;
- track progress;
- exam average/pass rate;
- attendance rate;
- assignment completion rate.

The service must use organization and enrollment boundaries and avoid N+1 query patterns in class/admin dashboards. Cached/materialized summaries may be added only after correctness is established.

## Dashboards

### Student
- Profile
- Current class/section
- Today's attendance
- Attendance rate
- Courses/tracks
- Upcoming/available exams
- Published results
- Course/track progress

### Teacher
- Assigned classes
- Today's attendance
- Students needing attendance correction
- Class course/track assignments
- Student progress
- Exam evaluation/result publication where authorized

### Owner/Admin
- Organization student counts
- Class/section counts
- Attendance rate and absent/late counts
- Learning completion
- Exam performance
- Results pending publication
- Student performance/attendance filters
- Device health/last-seen information

## Permission matrix

| Capability | Owner | Admin | Staff/Teacher | Student | Guardian |
|---|---:|---:|---:|---:|---:|
| Manage organization students | Yes | Yes | Limited assigned-class operations | No | No |
| Create/manage classes/sections | Yes | Yes | No | No | No |
| Manage academic years | Yes | Yes | No | No | No |
| Assign teacher to class | Yes | Yes | No | No | No |
| Add student to organization | Yes | Yes | No | No | No |
| Enroll existing org student in assigned class | Yes | Yes | Yes, assigned class only | No | No |
| Assign resource to individual student | Yes | Yes | Yes, permitted students | No | No |
| Assign resource to class | Yes | Yes | Yes, assigned class | No | No |
| View assigned-class students | Yes | Yes | Yes | Self only | Linked child only |
| Edit student admin/enrollment fields | Yes | Yes | No | No | No |
| Edit own student profile | No | No | No | Yes | No |
| Record/correct attendance | Yes | Yes | Assigned classes | No | No |
| Configure attendance devices/rules | Yes | Yes | No | No | No |
| View attendance | Organization | Organization | Assigned classes | Own | Linked child |
| Evaluate/manage results | Yes | Yes | Authorized classes/exams | No | No |
| Publish/unpublish results | Yes | Yes | Configurable/authorized | No | No |
| View published results | Yes | Yes | Authorized students | Own | Linked child |
| View progress | Organization | Organization | Assigned classes | Own | Linked child |
| Receive absence notifications | Optional | Optional | Assigned classes | Optional | Configurable |

## Tenant/security requirements
- Every student, guardian, academic, attendance and result query is scoped to the resolved organization.
- Cross-organization student/class/device/result access returns denial, not an empty-data fallback that could leak existence.
- Device ingestion cannot select an arbitrary organization through request data alone; the authenticated device determines the tenant.
- Student self-service endpoints use the logged-in user and resolved organization; never accept a user ID as the source of ownership.
- Teacher scope is derived from active `ClassTeacher` assignments.
- Attendance corrections create audit entries with actor, previous state and new state.
- Result publication creates audit entries.
- Device raw events are retained for troubleshooting and idempotency.

## Rollout

1. Student/guardian/academic models and enrollment.
2. Student profile dashboard and class-scoped teacher workspace.
3. Class/student learning assignments and effective-access integration.
4. Attendance records, rules and manual attendance.
5. Device registry, identifier mapping and ingestion API/adapter interface.
6. Absence finalization and email/SMS notification infrastructure.
7. Result publication layer on existing exam attempts.
8. Progress service and dashboards.
9. Reporting/export and advanced analytics.

Each phase is independently tested and migrated. Existing organization content/assignment behavior must remain regression-safe.

## Non-goals for first implementation
- No facial recognition implementation in core NPTOR.
- No vendor-specific device SDK embedded in the core domain.
- No mandatory Celery/Redis deployment requirement.
- No manual progress percentage editing.
- No automatic result publication immediately after exam submission; publication remains an explicit organization action.
