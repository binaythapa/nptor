# Course and Track Subscription Actions

## Status

Design specification for review. This document defines the intended behavior before implementation.

## Objective

Make course and track discovery more convenient by displaying a clear action on every course/track card wherever these resources are listed. Users should be able to subscribe to free resources immediately and find all acquired resources from **My Learning** without repeatedly returning to the marketplace.

## Confirmed product rules

1. Courses and tracks are two different resource types.
2. A course subscription grants access to that course only.
3. A track subscription grants access to the track and all courses included in that track.
4. Purchasing or subscribing to a course does not unlock its parent track.
5. Purchasing or subscribing to a track does not require separate purchases for its included courses.
6. Free-resource enrollment is immediate: clicking **Subscribe Free** creates the required enrollment/access records and makes the resource available in **My Learning** without approval.
7. Both courses and tracks appear independently in **My Learning**.

## User-facing behavior

For authenticated users, resource cards should expose a context-aware primary action:

- Free resource without access: **Subscribe Free**
- Paid resource without access: **Buy**
- Resource already accessible: **Continue Learning**
- Completed resource: retain a completion-aware state where the existing product supports it

For unauthenticated users, the action should direct the user through the existing authentication flow and preserve the intended resource/action where possible.

The same action behavior should be available wherever course or track cards are rendered, including the marketplace, domain/category listings, related resource sections, and other reusable catalog surfaces. Existing visual design and accessibility conventions should be preserved.

## Access and enrollment behavior

### Course

- Resolve the selected course and verify that it is publicly available and eligible for enrollment.
- If the course is free, create or reuse the user's course enrollment/access using the existing access service or enrollment mechanism.
- If the course is paid, route to the existing purchase/payment flow; do not silently grant access.
- Repeated requests must be idempotent and must not create duplicate enrollment or access records.

### Track

- Resolve the selected track and verify that it is publicly available and eligible for enrollment.
- If the track is free, create or reuse track access and grant access to every course explicitly included in that track.
- If the track is paid, route to the existing purchase/payment flow; after successful payment, grant track access and access to all included courses according to the existing access model.
- The track operation must be idempotent. Existing course access must be preserved and must not be duplicated.
- Courses included in a track are treated as included resources for track access, but they remain separate resources in the UI and in direct course-subscription logic.

No new parallel payment, entitlement, or enrollment system should be introduced if the repository already provides a suitable service. The implementation must reuse and extend the existing access-control and subscription abstractions.

## My Learning behavior

My Learning should present independently acquired resources in a single, coherent hub:

- Individually subscribed/purchased courses appear as course entries.
- Subscribed/purchased tracks appear as track entries.
- A track entry exposes its included courses and their learning state.
- Courses unlocked through a track should be reachable from the track and should not be represented as separate direct purchases.
- Directly acquired courses remain visible even when they are not associated with an acquired track.
- Existing progress, completion, and resume behavior must be retained.

The implementation should avoid duplicate cards for the same resource and should use stable resource identifiers when combining direct and track-derived access.

## Suggested implementation boundaries

1. **Resource-action resolution:** centralize the logic that determines whether a card shows Subscribe Free, Buy, Continue Learning, or another existing state.
2. **Course enrollment endpoint/service:** add or adapt an authenticated, POST-only flow for immediate free-course enrollment and reuse existing paid-course checkout behavior.
3. **Track enrollment endpoint/service:** add or adapt an authenticated, POST-only flow for immediate free-track enrollment, including access propagation to included courses.
4. **Reusable card UI:** update shared course and track card templates/components so actions are consistent everywhere.
5. **My Learning aggregation:** extend the existing My Learning query/context to include independently acquired courses and tracks while preserving current progress information.
6. **Authorization and integrity:** enforce server-side ownership/access checks, CSRF protection for browser requests, public/active resource checks, and idempotency.

Exact file and model changes must be determined from the current implementation during planning; this specification intentionally does not prescribe a new data model without inspecting the existing one.

## Error handling and UX

- Show a clear success message after free enrollment and provide a direct link to My Learning or the resource.
- If the resource is unavailable, show a safe user-facing error and do not create access.
- If the user already has access, do not create a second enrollment; redirect or respond with the existing-access state.
- If a track contains an invalid or unavailable course, the operation must follow a defined transactional policy: do not leave a partially granted track subscription. The implementation should use a database transaction and report the failure for administrator review.
- Paid flows must remain unchanged except for integrating the shared action-state presentation.

## Testing requirements

Automated tests should cover at least:

- Free course subscription creates access exactly once.
- Free track subscription creates track access and access to every included course exactly once.
- Course subscription does not grant parent-track access.
- Track subscription grants included-course access without creating direct course purchases.
- Duplicate clicks/retries are idempotent.
- Paid course and paid track actions continue to use the existing payment flow.
- Unauthenticated users are handled safely.
- Resource actions render correctly across all shared card/listing surfaces.
- My Learning shows direct courses, tracks, and track-included courses without duplicate entries.
- Existing certification, exam, progress, and access-control behavior does not regress.
- Mobile layout and keyboard/screen-reader accessibility remain usable.

## Out of scope

- Replacing the existing payment provider or payment architecture.
- Introducing certificates or certificate verification.
- Redesigning the entire marketplace or My Learning page.
- Changing the meaning of an existing course or track, or merging the two resource types.
- Automatically granting a track when a user purchases an individual course.
