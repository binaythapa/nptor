# Commerce and entitlement architecture

## Sellable products

NPTOR sells only these product types:

1. **Course** — access to the course and the exams attached to its quiz lessons.
2. **Track** — access to the track and the courses/exams included by the track.
3. **All-access subscription** — monthly or yearly access to the whole platform.

Individual exams are not a sellable product. Existing historical exam payment records remain readable, but new checkout/admin purchase flows do not offer an exam target.

## Access precedence

For a user requesting a course, track, or exam:

1. A valid all-access subscription grants platform-wide access.
2. A valid direct course entitlement grants the course and its course-lesson exams.
3. A valid direct track entitlement grants the track and its included resources.
4. Otherwise the resource remains locked.

Purchased course/track access is independent of an all-access subscription, so an expired all-access subscription does not revoke a separately purchased course or track.

## Payment flow

`Product/Plan -> PaymentOrder -> PaymentTransaction -> PaymentFulfillmentService -> Subscription/Entitlement/ResourceAccess`

Manual admin payments use the same entitlement rules and additionally create a `PaymentRecord` audit row.

## Subscription plans

`SubscriptionPlan.scope` distinguishes resource pricing from platform-wide pricing:

- `resource`: attached to a course or track.
- `all_access`: available as a platform-wide monthly/yearly plan.

`duration_days` controls the access period. Automatic recurring charging is deliberately gateway-dependent; the current implementation records `auto_renew` capability but does not invent a gateway-specific recurring billing mechanism.

## Track contents

Tracks can contain reusable exams through `TrackExam` and courses through `ExamTrack.courses`. A track purchase therefore provides a single entitlement at the track level while access checks can resolve the included course/exam content.
