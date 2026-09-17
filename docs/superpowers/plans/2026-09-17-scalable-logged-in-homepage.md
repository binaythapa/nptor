# Scalable Logged-in Homepage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the authenticated homepage redirect with a bounded, personalized dashboard that remains performant and usable with thousands of resources.

**Architecture:** Reuse the existing Django homepage route and Bulma-based templates. Add bounded, database-limited dashboard context for authenticated users, preserve public-home behavior for guests, and render reusable sections with explicit “View all” navigation rather than client-side expansion of large querysets. Organization-assigned resources must remain distinct from public paid resources.

**Tech Stack:** Django ORM, Django templates, Bulma, existing NPTOR models and URL routes, Django test framework.

**Spec:** Approved in-chat design for the scalable logged-in homepage on 2026-09-17.

## Global Constraints

- The homepage must never load thousands of resource records.
- Homepage collections must have explicit database-level limits.
- “View all” links must lead to dedicated paginated/filterable resource pages where those routes already exist.
- Organization-assigned resources must not be treated as subscription-controlled public premium resources.
- Preserve the existing visual language; avoid an unrelated redesign.
- Existing guest homepage behavior must remain functional.

---

### Task 1: Audit the authenticated dashboard flow and available routes

**Files:**
- Inspect: `pages/views.py`
- Inspect: `templates/pages/home.html`
- Inspect: relevant quiz dashboard views/templates, course views, organization views, and URL configuration
- Test: existing project test suite

- [ ] **Step 1: Identify the current authenticated redirect target and its context.**
- [ ] **Step 2: Identify existing URLs for practice, exams, courses, tracks, assigned resources, and learning history.**
- [ ] **Step 3: Identify models and relationships needed for bounded personalized queries.**
- [ ] **Step 4: Record any missing routes that should be represented by safe fallback links rather than invented URLs.**
- [ ] **Step 5: Run the relevant existing tests before modifications.**

### Task 2: Add bounded authenticated homepage context

**Files:**
- Modify: `pages/views.py`
- Test: `pages/tests.py` or the project’s established view-test location

**Interfaces:**
- Produces a homepage context containing bounded collections such as `continue_learning`, `organization_resources`, `recommended_resources`, `featured_courses`, `featured_tracks`, and `latest_exams`, plus aggregate learning metrics where the existing models support them.

- [ ] **Step 1: Write tests proving authenticated requests render the homepage rather than redirecting to the dashboard.**
- [ ] **Step 2: Write tests proving homepage resource collections are capped at their defined limits.**
- [ ] **Step 3: Write tests proving guest requests retain the existing public-home context and behavior.**
- [ ] **Step 4: Implement small helper functions in `pages/views.py` or a focused service module for bounded homepage queries.**
- [ ] **Step 5: Use `select_related`/`prefetch_related` only for relationships actually rendered.**
- [ ] **Step 6: Keep organization-assigned resources in a separate context collection and do not apply public subscription filtering to them.**
- [ ] **Step 7: Run the focused tests and fix failures.**

### Task 3: Replace the homepage template with a scalable dashboard layout

**Files:**
- Modify: `templates/pages/home.html`
- Inspect/modify only if necessary: existing student layout and theme CSS

- [ ] **Step 1: Write template-level tests or view assertions for the major authenticated sections and access labels.**
- [ ] **Step 2: Add Welcome and Quick Actions with stable action links.**
- [ ] **Step 3: Add My Learning Overview using aggregate values only.**
- [ ] **Step 4: Add Continue Learning and My Organization sections with small bounded previews and “View all” links.**
- [ ] **Step 5: Add bounded Recommended, Featured Courses, Certification Tracks, and Latest Mock Exams sections.**
- [ ] **Step 6: Remove the existing client-side “Show More” behavior that encourages unbounded homepage expansion.**
- [ ] **Step 7: Add empty states that do not create excessive page height.**
- [ ] **Step 8: Preserve guest fallback content and authentication calls to action.**
- [ ] **Step 9: Run template/view tests and manually inspect responsive markup.**

### Task 4: Verify performance, access separation, and regression safety

**Files:**
- Modify: relevant tests discovered during Tasks 1–3
- Inspect: `pages/views.py`, `templates/pages/home.html`

- [ ] **Step 1: Add assertions that homepage querysets are sliced or otherwise bounded.**
- [ ] **Step 2: Add an organization-member test ensuring assigned resources appear independently of public payment/subscription state.**
- [ ] **Step 3: Add a non-organization user test ensuring organization-only content is not exposed.**
- [ ] **Step 4: Run the focused Django tests.**
- [ ] **Step 5: Run the full available test suite.**
- [ ] **Step 6: Review the diff for accidental changes to unrelated homepage or payment behavior.**
- [ ] **Step 7: Commit the implementation with a focused message.**

