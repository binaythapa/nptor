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

A learner should be able to go from **Explore → Domain → Category/filter → Resource → Enroll/Buy/Start** without scanning a long unstructured list.

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
- one primary action

## Data/Authorization Rules

- Only publicly discoverable/published resources appear in the public student marketplace.
- Organization-owned resources must remain subject to organization visibility rules and should not leak through platform catalogue queries.
- Domain/category filters must be scoped consistently with the selected resource's organization.
- A resource can appear as “Buy” or “Enroll” when it is not currently entitled; this is not the same as being locked.
- Prerequisite/progression locks continue to be calculated by the existing catalogue/access logic.

## Performance Rules

- Query only fields/relations needed for cards.
- Use `select_related`/`prefetch_related` deliberately.
- Avoid per-card access queries where a bulk representation can be used.
- Pagination is mandatory for large result sets.
- Client-side filtering is acceptable only for small local UI controls; the authoritative catalogue filtering/search is server-side.

## Responsive/Accessibility Rules

- Preserve compact typography on desktop and mobile.
- Keyboard-accessible search, filters, tabs, and cards.
- Visible focus states.
- Semantic headings and landmarks.
- Respect reduced-motion preferences.
- Avoid horizontal overflow at narrow widths.

## Non-Goals

- No replacement of the existing payment/entitlement architecture.
- No redesign of course player or exam attempt pages.
- No duplicate Domain model.
- No mandatory new Domain FK on every resource in this phase when the existing classification graph can derive it safely.
- No loading hundreds of resources into the browser for filtering.

## Acceptance Criteria

1. A learner can discover Snowflake, AWS, Azure, etc. from a domain-first catalogue.
2. A domain can contain many courses, many tracks, and many exams without a visually overwhelming list.
3. Search can find a specific course/exam/track without manual scrolling.
4. Category and other filters narrow results server-side.
5. Pagination prevents large result payloads.
6. Purchased/assigned resources remain represented correctly in My Learning.
7. Catalogue actions route to the existing enrollment/checkout/start flows.
8. Unauthorized/private/unpublished resources are not exposed.
9. Existing access and payment tests continue to pass.
10. The UI remains usable on mobile and keyboard navigation.
