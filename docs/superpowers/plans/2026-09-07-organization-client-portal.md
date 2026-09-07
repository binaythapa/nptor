# Organization Client Portal — Implementation Plan

## Goal
Implement the approved multi-tenant organization/client portal architecture in the existing Django platform while preserving current organization authorization, assignments, subscriptions, and learning access behavior.

## Guardrails
- `Organization` remains the tenant identity and tenancy boundary.
- Do not create separate Django projects/databases per client.
- Keep `ResourceAccess` as the final authorization boundary.
- Portfolio visibility never grants learning access.
- Existing `/org/<slug>/` behavior and organization admin routes remain compatible.
- Custom domains are modeled and resolved only after verification; initial rollout may use slug URLs.
- Existing data is migrated additively.
- Avoid destructive deletes during rollout; deprecated fields/code are retained or marked `to be deleted` until tests pass.
- All tenant-scoped queries use the resolved organization context.

## Phase 1 — Domain models and migrations
1. Add `OrganizationProfile` for public/client identity and contact information.
2. Add `OrganizationPortalConfig` for branding, hero content, visibility flags, and publish state.
3. Add `OrganizationDomain` for slug/custom-domain mapping and verification state.
4. Add `OrganizationPortfolioSection` for controlled portfolio sections and ordering.
5. Export models through `organizations.models` and register admin support where appropriate.
6. Add migrations that create missing profile/config defaults for existing organizations without changing existing authorization records.
7. Preserve existing `Organization.logo` and `primary_color` as compatibility sources; new profile/config values become the canonical presentation layer after migration.

## Phase 2 — Tenant resolution and portal services
1. Introduce a tenant resolver service that resolves `/org/<slug>/` and verified custom hosts.
2. Extend middleware so URL/domain tenant context is established before portal/admin behavior.
3. Keep user `active_org` behavior for backward compatibility, but do not use it as the authoritative tenant for explicit organization URLs.
4. Add `OrganizationPortalService` for safe defaults, published configuration, portfolio sections, and course/track/exam presentation.
5. Add `OrganizationDomainService` for normalization, uniqueness, verification, primary-domain rules, and activation.
6. Add cache keys containing organization identity wherever portal data is cached.

## Phase 3 — Public portfolio portal
1. Add public organization portal URL `/org/<slug>/`.
2. Render organization profile, branding, hero, about, featured learning, achievements/testimonials/contact, and footer based on published configuration.
3. Ensure unpublished/inactive organizations do not expose private content.
4. Link featured learning to existing course/track/exam detail pages without bypassing `ResourceAccess`.
5. Add responsive/mobile-first templates and safe image handling.

## Phase 4 — Organization student portal
1. Add `/org/<slug>/learning/`.
2. Require authentication and active membership in the resolved organization.
3. Show only organization-scoped learning and assignments.
4. Continue using existing access/assignment services for authorization.
5. Add branded progress, assignments, exams, and achievements presentation.

## Phase 5 — Organization admin console
1. Refactor the existing dashboard view into dashboard service modules.
2. Add KPI/attention/activity/learning-performance sections.
3. Expand navigation to People, Learning, Assignments, Analytics, Portfolio, and Settings while retaining existing routes.
4. Add portfolio profile/branding/homepage editors and draft-preview-publish workflow.
5. Add organization settings and domain management with capability checks.
6. Preserve existing assignment/course management services and tenant isolation.

## Phase 6 — Analytics and audit
1. Add dashboard service queries that avoid N+1 progress queries.
2. Add student/course/assignment/exam performance summaries.
3. Add audit records for branding, publishing, domain, role, settings, assignment, and student-management actions where an existing audit mechanism is available; otherwise introduce a minimal organization audit model/service.

## Phase 7 — Custom domain readiness
1. Support exact verified host matching through `OrganizationDomain`.
2. Enforce normalized-domain uniqueness and one primary domain per organization.
3. Require DNS verification token before activation.
4. Respect Django trusted-host configuration.
5. Keep `/org/<slug>/` available as the canonical fallback during initial rollout.

## Testing strategy
- Model validation and migration tests.
- Tenant resolution tests for slug and custom domain.
- Cross-tenant URL/query isolation tests.
- Role/capability tests for owner/admin/staff/student.
- Public vs authenticated portal tests.
- Inactive/unpublished organization tests.
- Portfolio draft vs published tests.
- Domain verification/collision/primary-domain tests.
- Course visibility vs `ResourceAccess` tests.
- Existing assignment/access regression suite.
- Dashboard query/performance regression tests.
- Responsive template tests for key admin and portal pages.

## Rollout order
Models → migrations → tenant resolver/services → public portal → student portal → admin dashboard/portfolio → analytics/audit → custom-domain activation.

## Git workflow
Work only on `feature/organization-client-portal`. Use small logical commits. Verify each phase before proceeding. Do not merge into `main` until the full test suite and security regression checks pass.
