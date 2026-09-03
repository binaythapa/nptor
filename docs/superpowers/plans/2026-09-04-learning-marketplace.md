# Learning Marketplace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a scalable domain-first student learning marketplace for courses, exam tracks, and exams with server-side search, filtering, sorting, and pagination.

**Architecture:** Extend the existing catalogue service rather than replacing access/payment architecture. Introduce a domain-first catalogue view plus a domain hub, with query-string filters and paginated resource result sets. Derive resource domains from existing Category relationships and derive track domains from their published exams in this phase.

**Tech Stack:** Django, Django ORM/querysets, existing quiz/courses/subscriptions models and AccessService, Django templates, existing student CSS/JS.

**Spec:** `docs/superpowers/specs/2026-09-04-learning-marketplace-design.md`

## Global Constraints

- Domain is the primary discovery layer.
- Search and authoritative catalogue filtering are server-side.
- Pagination is mandatory for large result sets.
- Existing payment/entitlement/access architecture remains authoritative.
- My Learning remains separate from marketplace discovery.
- Organization visibility boundaries must not be weakened.
- Preserve compact typography and responsive/accessibility requirements.
- Do not add redundant Domain foreign keys when the existing classification graph can safely derive the domain.

---

### Task 1: Establish domain catalogue service contract

**Files:**
- Create: `quiz/services/learning_catalog.py`
- Test: `quiz/test_learning_catalog.py`

**Interfaces:**
- Consumes: existing `Domain`, `Category`, `Course`, `ExamTrack`, `Exam`, and visibility/access helpers.
- Produces: `build_learning_catalog(*, user, domain=None, query="", resource_type="all", category=None, level=None, access=None, page=1, per_page=...)` returning domain summaries and paginated resource groups.

- [ ] Write failing tests for domain summaries and resource-domain resolution.
- [ ] Run the focused tests and verify they fail for the missing service.
- [ ] Implement the smallest service that builds active platform domains and derives resource membership through existing categories/exams.
- [ ] Run the focused tests again.
- [ ] Add tests for organization isolation and unpublished/private resources.
- [ ] Run the focused suite.
- [ ] Commit the service and tests.

### Task 2: Add server-side search/filter/pagination behavior

**Files:**
- Modify: `quiz/services/learning_catalog.py`
- Test: `quiz/test_learning_catalog.py`

**Interfaces:**
- Consumes: Task 1 service contract.
- Produces: stable query-string-driven filtering for domain, category, resource type, level, free/paid, duration where applicable, and search; paginated results.

- [ ] Write failing tests for search across course/exam/track titles and category/domain names.
- [ ] Run focused tests to verify RED.
- [ ] Add failing tests for resource type, category, level, price/free and pagination.
- [ ] Implement ORM filters with `Q` expressions, distinct handling, and pagination.
- [ ] Run focused tests and refactor only after green.
- [ ] Add tests for empty/invalid filter values and page bounds.
- [ ] Commit the service enhancement and tests.

### Task 3: Build marketplace landing page

**Files:**
- Modify: `quiz/views/exam_list.py`
- Modify: `quiz/urls/urls.py`
- Modify: `templates/quiz/student/exam/exam_list.html`
- Create: `static/css/pages/learning_marketplace.css`
- Test: `quiz/test_learning_marketplace_view.py`

**Interfaces:**
- Consumes: `build_learning_catalog` from Task 2.
- Produces: authenticated marketplace route with search, domain cards, filter controls, and paginated mixed resource results.

- [ ] Write failing view tests for the domain-first landing page.
- [ ] Verify RED.
- [ ] Implement GET query parsing and service invocation.
- [ ] Add domain cards with counts and links to domain hubs.
- [ ] Replace the current long unstructured catalogue presentation with compact marketplace sections while preserving action URLs.
- [ ] Add accessible search/filter controls and pagination links.
- [ ] Run focused view/template tests.
- [ ] Add responsive CSS and reduced-motion rules.
- [ ] Commit landing page changes.

### Task 4: Add domain hub

**Files:**
- Modify: `quiz/views/exam_list.py` or create `quiz/views/learning_marketplace.py` if separation is cleaner
- Modify: `quiz/urls/urls.py`
- Create: `templates/quiz/student/domain_hub.html`
- Test: `quiz/test_learning_domain_hub.py`

**Interfaces:**
- Consumes: domain slug/id and Task 2 catalogue service.
- Produces: `/quiz/learning/domain/<slug>/` (or equivalent named route) showing scoped Courses, Exam Tracks, Exams, categories, filters, search, and pagination.

- [ ] Write failing tests for valid domain rendering.
- [ ] Add tests that resources from another domain are excluded.
- [ ] Implement the domain route and 404 behavior for inactive/nonexistent domains.
- [ ] Render compact grouped results and breadcrumb navigation.
- [ ] Add category navigation scoped to the domain.
- [ ] Run focused tests.
- [ ] Commit domain hub.

### Task 5: Preserve and test access/payment action semantics

**Files:**
- Modify: `quiz/services/learning_catalog.py` only if needed
- Test: `quiz/test_learning_marketplace_access.py`

**Interfaces:**
- Consumes: existing `AccessService`, subscription/entitlement state, and checkout routes.
- Produces: result actions that distinguish access, enroll, buy, subscribe, free start, and prerequisite lock without granting access.

- [ ] Write failing tests for entitled, unentitled-paid, free, locked, and organization-scoped resources.
- [ ] Verify RED.
- [ ] Implement action metadata by reusing existing catalogue/access rules.
- [ ] Run focused tests.
- [ ] Confirm checkout/start URLs remain unchanged.
- [ ] Commit access semantics.

### Task 6: Final responsive/accessibility and regression verification

**Files:**
- Modify: `static/css/pages/learning_marketplace.css`
- Modify: relevant marketplace templates
- Test: existing catalogue/dashboard/access test suites plus new marketplace tests

- [ ] Add tests for keyboard-visible labels, semantic headings, pagination links, and filter query preservation where practical.
- [ ] Run all relevant Django test modules available in the repository.
- [ ] Run `python manage.py check` if the environment is available.
- [ ] Review query counts/ORM structure for obvious N+1 patterns.
- [ ] Verify git diff and changed-file scope.
- [ ] Commit final cleanup.
- [ ] Do not claim runtime tests passed unless command output confirms it.
