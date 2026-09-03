# Learning Marketplace — Domain-First Catalogue Design

**Status:** Approved
**Date:** 2026-09-04

## Goal

Make the student learning catalogue scalable for hundreds of courses, exams, and tracks by making Domain the primary discovery layer while preserving existing access, payment, and organization boundaries.

## Product Model

```text
Learning Marketplace
└── Domain (Snowflake, AWS, Azure, Python, ...)
    └── Category / Subcategory
        ├── Courses
        ├── Exam Tracks
        │   └── Exams
        └── Standalone Exams
```

A learner should be able to go from **Explore → Domain → Category/filter → Resource → Start/Preview → Paywall → Checkout → Continue** without scanning a long unstructured list.

## Core Decisions

1. **Domain-first navigation**
   - The catalogue opens with active domains and useful resource counts.
   - Selecting a domain scopes the marketplace to that learning ecosystem.
   - Domain pages expose Courses, Exam Tracks, and Exams together.

2. **Reuse existing classification**
   - `Domain` remains the canonical top-level classification.
   - `Category.domain` remains the existing category-to-domain relationship.
   - Courses and exams should use their existing category relationships where possible.
   - Tracks can derive their domain from the domains represented by their published exams instead of introducing a redundant domain foreign key in this phase.

3. **Global search**
   - One search field searches across visible courses, tracks, exams, domains, and relevant category names.
   - Search is server-side so the UI remains performant with hundreds/thousands of records.

4. **Filtering**
   - Domain is the primary scope.
   - Within a domain, support resource type, category, level, free/paid, and duration where applicable.
   - Filters are query-string based so results are bookmarkable and navigable.

5. **Sorting and pagination**
   - Default sorting favors relevant/new resources without changing authorization semantics.
   - Provide newest and price sorting where meaningful.
   - Use server-side pagination; do not render hundreds of cards at once.

6. **My Learning stays separate**
   - Purchased, subscribed, assigned, and otherwise entitled resources belong in the existing student dashboard.
   - The marketplace is discovery; it must not become an authorization source.

7. **Access and payment remain authoritative**
   - Existing `AccessService`, entitlements, subscriptions, checkout, and fulfillment rules remain the source of truth.
   - Catalogue buttons must reflect access state but must never grant access.

8. **Start before purchase**
   - Paid courses expose a controlled first-lesson preview without granting entitlement or recording progress.
   - Paid exams expose a bounded sample without creating a `UserExam` attempt or consuming an attempt.
   - Full course/exam access remains protected by the existing access layer.
   - After successful payment, a safe same-site return destination can resume the learner into the purchased resource.

9. **Learning shortlist**
   - Authenticated learners can save courses, exams, and tracks to a persistent shortlist/watchlist.
   - Shortlisting never grants access and does not alter payment state.
   - Shortlist mutations are POST-only and CSRF protected.
   - The student dashboard shows the user's current shortlist and removes unpublished/private resources from display.

## User Experience

### Marketplace landing

- Compact hero: “Learn, Practice, Certify”.
- Prominent search field.
- Domain cards/chips showing name and counts.
- Optional “Popular”/“Recommended” area when reliable data exists.
- Recent/featured resources should not displace domain discovery.

### Domain hub

- Breadcrumb: Learning → Domain.
- Domain title and short description.
- Category chips/tree for narrowing the domain.
- Tabs or compact sections:
  - Courses
  - Exam Tracks
  - Exams
- Search remains available inside the domain.
- Results use compact cards/rows consistent with the current catalogue visual direction.

### Resource results

Each result exposes only decision-useful information:
- title
- resource type
- category/domain context
- level where applicable
- duration/questions where applicable
- price/free state
- current access state
- shortlist state
- one primary action

### Start / preview / paywall

- A paid resource should not force a purchase before the learner can understand what they are getting.
- Course: **Start → first preview lesson → Get full access → checkout → continue course**.
- Paid exam: **Try → bounded sample → Get full access → checkout → start real exam**.
- Free resources continue directly into their existing start flow.
- Preview must never create paid entitlements, completion records, or real exam attempts.

### Shortlist / watchlist

- Each course, exam, and track card has an accessible star/bookmark control.
- Toggle is AJAX with a normal POST form fallback.
- Dashboard includes **Your Shortlist** near Continue Learning.
- Shortlisted resources remain useful whether purchased or not; the action changes from preview/start to continue when access is granted.

## Data/Authorization Rules

- Only publicly discoverable/published resources appear in the public student marketplace.
- Organization-owned resources must remain subject to organization visibility rules and should not leak through platform catalogue queries.
- Domain/category filters must be scoped consistently with the selected resource's organization.
- A resource can appear as “Start”/“Try” when a controlled preview exists; this is not the same as granting access.
- Prerequisite/progression locks continue to be calculated by the existing catalogue/access logic.
- Shortlist records are always scoped to the authenticated user.
- Checkout return targets must be same-site paths; external/open redirects are rejected.

## Performance Rules

- Query only fields/relations needed for cards.
- Use `select_related`/`prefetch_related` deliberately.
- Avoid per-card access queries where a bulk representation can be used.
- Pagination is mandatory for large result sets.
- Client-side filtering is acceptable only for small local UI controls; the authoritative catalogue filtering/search is server-side.

## Responsive/Accessibility Rules

- Preserve compact typography on desktop and mobile.
- Keyboard-accessible search, filters, tabs, cards, and shortlist controls.
- Visible focus states.
- Semantic headings and landmarks.
- Respect reduced-motion preferences.
- Avoid horizontal overflow at narrow widths.

## Non-Goals

- No replacement of the existing payment/entitlement architecture.
- No full redesign of course player or exam attempt pages.
- No duplicate Domain model.
- No mandatory new Domain FK on every resource in this phase when the existing classification graph can derive it safely.
- No loading hundreds of resources into the browser for filtering.
- No real exam attempt or lesson progress from preview mode.

## Acceptance Criteria

1. A learner can discover Snowflake, AWS, Azure, etc. from a domain-first catalogue.
2. A domain can contain many courses, many tracks, and many exams without a visually overwhelming list.
3. Search can find a specific course/exam/track without manual scrolling.
4. Category and other filters narrow results server-side.
5. Pagination prevents large result payloads.
6. Purchased/assigned resources remain represented correctly in My Learning.
7. A learner can start a controlled preview before purchasing a paid course/exam.
8. Reaching full-content boundaries leads to the existing checkout/entitlement flow.
9. Successful payment can safely resume the intended learning destination.
10. A learner can shortlist and remove courses, exams, and tracks.
11. The dashboard shows the learner's own shortlist and excludes stale/private resources.
12. Unauthorized/private/unpublished resources are not exposed.
13. Existing access and payment tests continue to pass.
14. The UI remains usable on mobile and keyboard navigation.