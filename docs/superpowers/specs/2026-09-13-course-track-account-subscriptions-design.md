# Course, Track, and Account Subscription Architecture

## Goal

Make Courses and Tracks the only directly sellable learning products, allow Exams to be reused across many Courses and Tracks, isolate Course and Track subscriptions, and add account-level plans that provide either complete platform access or a selectable quota of Courses and Tracks.

## Product Model

- A Course can contain many Exams through `CourseExam`.
- A Track can contain many Exams through the existing `TrackExam` model.
- A Course and a Track are independent; there is no Course-to-Track relationship.
- An Exam can belong to many Courses and many Tracks.
- Exams are not independently purchasable.
- Course plans sell Course access only.
- Track plans sell Track access only.
- Account plans can grant all Courses and Tracks or a limited selectable quota.

## Subscription Plan Model

`SubscriptionPlan` remains the centralized plan definition. It gains an explicit product type and access mode rather than creating separate subscription engines.

Product types:

- `course`
- `track`
- `account`

Access modes:

- `single_resource`: Course or Track plans grant access to the attached resource only.
- `limited_access`: Account plan permits the subscriber to select resources up to configured `max_courses` and `max_tracks` quotas.
- `all_access`: Account plan grants all Courses and all Tracks.

For limited account plans, resource selection is user-driven: a plan such as 5 Courses + 3 Tracks allows the user to choose any five Courses and any three Tracks. Exams become available only through selected/owned parent resources.

## Entitlements and Account Selections

`SubscriptionEntitlement` represents directly owned Course or Track resources. Exam subscription entitlements are removed from the subscription product model.

Account subscriptions are evaluated through an account access policy/selection layer instead of materializing one entitlement per Course/Track for an all-access account. Limited accounts store explicit Course/Track selections and enforce the plan quotas transactionally.

## Authorization Rules

Exam access succeeds only when one of the following is true:

1. A legitimate direct/admin/system access record grants the exam, where that legacy capability is intentionally retained for compatibility.
2. The user has valid Course access and the Exam is a member of that Course.
3. The user has valid Track access and the Exam is a member of that Track.

Course access can come from a Course subscription, an account subscription, or existing organization assignment/access. Track access can come from a Track subscription, an account subscription, or existing organization assignment/access.

A Course subscription never grants Track access. A Track subscription never grants Course access. Account subscriptions are the only subscriber-level source that can grant both resource types.

## Checkout and Administration

Checkout, subscription plan selection, and custom administration expose Courses, Tracks, and Account plans as purchasable products. Standalone Exam subscription actions are removed or converted to compatibility-safe no-ops where needed during migration.

## Migration Strategy

Existing database data must be preserved. Schema changes use additive migrations first. Deprecated Exam subscription relationships and legacy plan fields are retained temporarily where required for migration compatibility, then renamed or removed only after tests and data verification. No Course-to-Track relationship is introduced.

## UI and Catalog

Courses and Tracks are catalog products. Exams are displayed in the context of their parent Course/Track and are not presented as standalone purchasable products. Direct exam routes remain safe but enforce parent-resource authorization.

## Organization Access

Organization subscription/assignment access remains a separate authorization source and is not converted into account subscriptions. Existing organization tenant scoping and ResourceAccess remain authoritative.

## Verification

Add model, service, and authorization regression tests for relationship reuse, product isolation, account all-access, account quota selection, quota enforcement, exam inheritance, and removal of standalone exam purchasing. Run focused subscription/quiz/course tests, Django system checks, and the full test suite when practical.
