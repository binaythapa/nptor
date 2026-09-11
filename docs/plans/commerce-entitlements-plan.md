# Commerce entitlement implementation plan

- Add `SubscriptionPlan.scope` with `resource` and `all_access` values.
- Allow payment orders to target a subscription plan in addition to courses/tracks, while rejecting new exam purchases.
- Fulfill all-access orders as user subscriptions without a resource-specific entitlement.
- Add a platform-wide access check before resource-specific access checks.
- Add course membership to tracks and make track access resolve included courses.
- Ensure exams launched from a paid course are unlocked by course access.
- Add a subscription checkout for active all-access plans.
- Replace the custom manual-payment target model with Course / Track / All-access Subscription choices; do not expose Exam.
- Keep legacy exam payment records readable for audit compatibility.
- Add focused tests for plan scope, all-access access, course/track purchase boundaries, and manual-payment validation.
- Run Django checks and focused test suites before committing.
