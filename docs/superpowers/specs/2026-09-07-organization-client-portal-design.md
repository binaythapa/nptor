# Organization Client Portal & Multi-Tenant Architecture Design

**Date:** 2026-09-07  
**Status:** Design approved in chat; implementation not yet started

## 1. Purpose

Transform the existing `Organization` model into the foundation of a robust multi-tenant client platform. Each organization is a client with its own branded public portfolio, student learning portal, and organization administration console, while sharing the same Django application and database.

The first release uses `/org/<organization-slug>/` URLs. The architecture also supports verified custom domains such as `learn.client.com` without requiring a future tenant-model rewrite.

## 2. Goals

- Strict tenant isolation across organizations.
- Organization-specific branding and portfolio content.
- Separate public portfolio, student learning, and admin experiences.
- Reuse existing courses, tracks, exams, assignments, memberships, permissions, and `ResourceAccess` authorization.
- Draft/preview/publish workflow for portfolio changes.
- Organization admin dashboard with people, learning, assignments, analytics, portfolio, and settings.
- Future-ready custom-domain routing.
- Responsive/mobile-first interfaces.
- Auditable sensitive organization changes.
- Backward-compatible migration with no destructive deletion during rollout.

## 3. Non-Goals

- Separate Django projects/databases per client.
- Arbitrary customer-authored CSS or JavaScript.
- A fully general page-builder/CMS in the first release.
- Replacing `ResourceAccess` with portfolio visibility.
- Replacing the existing organization permission system.
- Requiring custom domains for launch.

## 4. Tenant Model

`Organization` remains the canonical tenant identity and official organization record. It continues to own the tenant slug, type, lifecycle state, creator, and existing compatibility fields.

The platform separates identity from presentation:

- `Organization`: tenancy and identity.
- `OrganizationProfile`: client-facing organization information.
- `OrganizationPortalConfig`: branding and portal behavior.
- `OrganizationPortfolioSection`: controlled portfolio sections/content.
- `OrganizationDomain`: hostname-to-tenant mapping for future custom domains.

Existing `Organization.name`, `Organization.logo`, and `Organization.primary_color` remain during migration. New presentation models become the preferred source of truth, with a compatibility/migration strategy so existing organizations do not lose branding.

## 5. Proposed Data Model

### OrganizationProfile

One-to-one with `Organization`.

Fields:

- `organization`
- `display_name`
- `tagline`
- `description`
- `logo`
- `cover_image`
- `favicon`
- `website`
- `email`
- `phone`
- `address`
- `city`
- `country`
- `social_links`
- `updated_at`

### OrganizationPortalConfig

One-to-one with `Organization`.

Fields:

- `organization`
- `primary_color`
- `secondary_color`
- `hero_title`
- `hero_subtitle`
- `hero_image`
- `welcome_message`
- `show_courses`
- `show_tracks`
- `show_exams`
- `show_about`
- `show_testimonials`
- `show_contact`
- `custom_footer_text`
- `is_published`
- `updated_at`

### OrganizationDomain

Maps verified hostnames to organizations.

Fields:

- `organization`
- `domain`
- `domain_type` (`NPTOR_SUBDOMAIN`, `CUSTOM`)
- `is_primary`
- `is_verified`
- `verification_token`
- `ssl_status`
- `created_at`

Constraints:

- A domain belongs to only one organization.
- An organization has at most one primary domain.
- A domain must be verified before active tenant resolution.

### OrganizationPortfolioSection

Controlled portfolio content.

Fields:

- `organization`
- `section_type`
- `title`
- `subtitle`
- `content`
- `image`
- `display_order`
- `is_enabled`
- `metadata`

Initial section types:

- Hero
- About
- Featured Courses
- Learning Programs
- Achievements
- Testimonials
- Contact
- Custom Text

## 6. User Experiences

### Public organization portal

`/org/<slug>/`

Provides the organization's branded portfolio and public learning catalog.

Typical sections:

- Header/logo/navigation
- Hero/banner
- Featured courses
- About
- Learning programs
- Achievements
- Testimonials
- Contact
- Footer/social links

### Organization student portal

`/org/<slug>/learning/`

Provides:

- Welcome/dashboard
- Continue Learning
- My Courses
- Assignments and due dates
- Upcoming exams
- Progress
- Achievements

It requires authentication, active organization membership, and applicable access authorization.

### Organization admin console

`/org/<slug>/admin/`

Navigation:

- Dashboard
- People: Students, Staff/Teachers, Groups/Classes, Invitations
- Learning: Courses, Learning Tracks, Exams, Questions
- Assignments: All, Create, Due/Overdue, History
- Analytics: Student, Course, Assignment, Exam performance
- Portfolio: Profile, Branding, Homepage, Featured Learning, Preview/Publish
- Settings: General, Access/Registration, Roles/Permissions, Domains, Subscription/Usage, Danger Zone

## 7. Tenant Resolution & Routing

Resolution order:

1. Verified custom-domain exact match.
2. `/org/<slug>/` resolution.
3. No implicit tenant selection from the logged-in user alone for tenant-scoped routes.

Request flow:

```text
Request
  -> tenant resolver
  -> Organization
  -> organization middleware/context
  -> permission/access checks
  -> portal/admin/learning service
  -> tenant-scoped template
```

Custom domains are intentionally supported by the architecture but can remain disabled until domain verification and deployment configuration are ready.

Hostnames must be normalized and matched exactly. No wildcard tenant mapping is used initially. Django trusted-host configuration remains part of deployment security.

## 8. Authorization & Isolation

Tenant context is established before business logic executes.

All tenant-scoped reads and writes must filter through the resolved organization. Shared helpers/services should prevent individual views from accidentally omitting the organization filter.

Existing `OrganizationMember`, `organizations.permissions`, and `ResourceAccess` remain authoritative:

- Membership determines whether a user belongs to the organization.
- Permission capabilities determine what an organization role may manage.
- `ResourceAccess` determines actual course/track/exam authorization.
- Portfolio visibility never grants learning access.

Recommended capabilities include:

- `can_view_dashboard`
- `can_manage_students`
- `can_manage_courses`
- `can_manage_assignments`
- `can_view_analytics`
- `can_manage_portfolio`
- `can_manage_settings`
- `can_manage_domains`

Cross-tenant resource tampering should not reveal another organization's existence; use consistent 404/403 behavior appropriate to the route, with 404 preferred for sensitive tenant-scoped resource lookups where practical.

## 9. Services & Application Boundaries

Introduce explicit service boundaries instead of putting tenant and dashboard logic directly into views.

```text
organizations/services/
  tenant.py
  portal.py
  domains.py
  dashboard/
    overview.py
    students.py
    courses.py
    assignments.py
    exams.py
    analytics.py
    activity.py
```

Responsibilities:

- `TenantResolver`: resolve organization from verified domain or slug.
- `OrganizationPortalService`: profile/config/portfolio read and publish behavior.
- `OrganizationDomainService`: domain normalization, verification, primary-domain rules.
- Dashboard services: efficient tenant-scoped KPI and analytics queries.

The existing dashboard view should become a thin orchestration layer.

## 10. Dashboard Design

Dashboard home should answer four questions:

1. How is the organization doing?
2. What needs attention?
3. What is happening with learning?
4. What should the admin do next?

KPIs:

- Active students
- Active courses
- Active assignments
- Average completion
- Active exams
- Completion rate

Attention indicators:

- Overdue assignments
- Not-started students
- Students falling behind
- Expiring access
- Upcoming exams
- Inactive students

Performance tables should use optimized aggregate queries and `select_related`/`prefetch_related` where appropriate. Avoid per-row progress queries/N+1 patterns.

## 11. Portfolio Publishing

Portfolio changes use:

```text
Draft -> Preview -> Publish
```

Editing does not immediately change the live public portal. Publishing makes the configuration/content active.

If caching is introduced, cache keys must include organization identity and publication/version state so content cannot leak between tenants.

Missing profile/configuration should have safe defaults and may be automatically initialized through a service/helper.

## 12. Media & Branding Security

Uploaded logo, cover, hero, favicon, and portfolio images must:

- Be validated as supported image types.
- Have size limits.
- Use organization-scoped upload paths.
- Never be treated as executable content.
- Be suitable for future image transformation/optimization.

Initial branding controls are limited to safe fields such as logo, cover image, colors, organization name, text, social links, and controlled typography. Arbitrary CSS/JS is excluded.

## 13. Auditability

Sensitive organization actions should be auditable, including:

- Branding changes
- Portfolio publish/unpublish
- Domain add/remove/verify
- Role changes
- Organization settings changes
- Student removal
- Assignment changes

The implementation should reuse any existing audit infrastructure where available rather than creating duplicate mechanisms.

## 14. Migration Strategy

Migration is additive and compatibility-first.

### Phase 1: Data model

- Add profile, portal config, domain, and portfolio-section models.
- Add migrations and indexes/constraints.
- Preserve existing organization fields.
- Initialize profile/config for existing organizations with safe defaults.
- Copy existing logo/color values into the new presentation layer where appropriate without immediately removing legacy fields.

### Phase 2: Portal

- Add organization public portal.
- Add student organization learning portal.
- Reuse existing course/track/exam/access services.
- Keep existing routes working during transition.

### Phase 3: Admin dashboard

- Refactor dashboard into service-backed sections.
- Add people, learning, assignments, analytics, portfolio, and settings navigation incrementally.

### Phase 4: Custom domains

- Add domain administration and verification.
- Enable exact-match verified-domain resolution.
- Validate deployment/SSL behavior before exposing to clients.

### Phase 5: Audit/optimization

- Complete audit coverage.
- Add query/index optimization.
- Add caching only after tenant isolation tests pass.

During testing/migration, do not immediately destructively delete existing structures. If old fields/routes/files must eventually be removed, prefer a temporary `to be deleted` naming/deprecation step, verify all tests and production behavior, then perform the final cleanup in a separate change.

## 15. Backward Compatibility

- Existing organization memberships and roles remain valid.
- Existing organization permission checks remain authoritative.
- Existing `ResourceAccess` behavior remains unchanged.
- Existing learning resources remain shared platform resources unless already organization-scoped.
- Existing organization routes should remain functional until their replacements are proven.
- Legacy branding fields remain until the new presentation layer is verified.

## 16. Testing Strategy

### Tenant isolation

- Organization A cannot access Organization B resources by slug manipulation.
- Organization A cannot resolve Organization B by custom domain.
- Inactive/unverified domains do not resolve.
- Inactive organizations do not expose live portals.

### Authorization

- Owner/admin/staff/student capabilities are enforced.
- Students cannot access admin console.
- Staff only see permitted administration functions.
- Organization membership is required for private organization experiences.
- Portfolio visibility cannot bypass `ResourceAccess`.

### Publishing

- Draft changes are invisible to public users.
- Preview reflects draft state.
- Publish updates live state.
- Unpublished portals show controlled public behavior.

### Domains

- Domain uniqueness.
- One primary domain per organization.
- Verification token flow.
- Exact hostname matching.
- Domain collision protection.

### Dashboard

- Tenant-scoped metrics.
- Role-based visibility.
- No N+1 query regressions for major dashboard tables.

### Security/regression

- Existing security tests continue to pass.
- Existing student-removal and exam mutation protections remain intact.
- Responsive tests cover key public, student, and admin pages.

## 17. Performance

- Prefer aggregate database queries for KPIs.
- Use `select_related`/`prefetch_related` for known relationships.
- Add indexes for tenant lookup, domain lookup, publication state, and common dashboard filters.
- Avoid repeated progress/access queries inside loops.
- Introduce caching only with organization/version-aware keys.

## 18. Proposed Repository Areas

Expected implementation areas include:

```text
organizations/
  models/
    organization.py              # preserve tenant identity
    profile.py                    # new
    portal.py                     # new
    domain.py                     # new
    portfolio.py                  # new
  services/
    tenant.py                     # new/refactor
    portal.py                     # new
    domains.py                    # new
    dashboard/
      overview.py
      students.py
      courses.py
      assignments.py
      exams.py
      analytics.py
      activity.py
  views/
    public/                       # organization portal
    student/                      # organization learning
    admin/                        # organization admin
  templates/organizations/
    public/
    student/
    admin/
  tests/
    tenant_isolation/
    portal/
    domains/
    dashboard/
    portfolio/
```

Exact file placement should be confirmed against the current repository structure before implementation rather than blindly creating duplicate modules.

## 19. Final Architecture Summary

```text
                         +----------------------+
                         |      HTTP Request     |
                         +----------+-----------+
                                    |
                         +----------v-----------+
                         |    Tenant Resolver    |
                         | slug / verified host |
                         +----------+-----------+
                                    |
                         +----------v-----------+
                         |     Organization      |
                         |      tenant context   |
                         +----+--------+---------+
                              |        |
                 +------------+        +----------------+
                 |                                     |
        +--------v---------+                 +---------v--------+
        | Portal Services  |                 | Permission/Auth  |
        | profile/config   |                 | membership/access|
        | portfolio        |                 +---------+--------+
        +--------+---------+                           |
                 |                                     |
       +---------+----------+               +----------+----------+
       |                    |               |                     |
+------v------+     +-------v------+  +-----v------+      +------v------+
| Public      |     | Student     |  | Admin      |      | Analytics   |
| Portfolio   |     | Learning    |  | Console    |      | & Activity  |
+-------------+     +-------------+  +------------+      +-------------+
```

This architecture keeps tenancy, presentation, authorization, learning resources, and administration cleanly separated while allowing the platform to grow from slug-based organization portals into verified custom-domain client portals.

## 20. Implementation Gate

This document represents the approved design. Implementation must not begin until the user reviews/approves this written specification and an implementation plan is subsequently created and approved according to the development workflow.
