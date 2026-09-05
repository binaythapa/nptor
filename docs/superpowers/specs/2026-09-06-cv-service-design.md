# NPTOR CV Service — Design Specification

## Goal

Add a standalone CV/resume creation service to NPTOR. A user must be able to create and maintain professional CVs without purchasing or completing NPTOR courses, tracks, or exams. Existing NPTOR learning/certification information is optional enrichment only.

## Product flow

1. User opens CV Builder.
2. NPTOR reuses authoritative account information already available to the signed-in user.
3. User can either start from scratch or upload an existing PDF/DOCX CV.
4. Uploaded CV content is parsed and converted into proposed structured career facts.
5. User reviews, confirms, edits, or rejects extracted facts.
6. A Master Career Profile stores reusable career information.
7. An AI-guided interview asks only for missing or useful details; users can skip AI and edit manually.
8. User creates one or more CVs from the master profile.
9. Each CV may select, override, or add information independently.
10. AI can assist with summaries, achievement bullets, skills, job tailoring, and ATS review, but must not invent unconfirmed factual claims.
11. User selects a template and previews the CV.
12. CV can be saved, duplicated, versioned, edited, and exported as PDF or DOCX.
13. User can request delivery through supported channels such as email, WhatsApp, or Viber; delivery attempts are recorded.

## Architecture

Create a dedicated Django `cv` app. The app owns career-profile, CV, template, AI, document-generation, and delivery concerns. It must not introduce foreign-key dependencies on quiz courses, exams, tracks, or question banks for core CV creation.

Core relationships:

```text
User
 ├── existing account/profile data
 └── MasterCareerProfile
       ├── education
       ├── experience
       ├── projects
       ├── skills
       ├── achievements
       └── certifications
             ↓
         CV / CVVersion
             ↓
          CVTemplate
             ↓
        PDF / DOCX / Delivery
```

## Data model principles

- `CareerProfile` is the reusable source of truth for confirmed career information.
- Career sections are structured records rather than a single blob or chatbot transcript.
- `CV` references a user's career profile but stores per-CV selections and overrides.
- `CVVersion` captures snapshots for reliable history and regeneration.
- `CVTemplate` is independent from content so the same CV can switch layouts without rewriting content.
- Uploaded source CVs are retained only as needed for extraction/audit and are not automatically treated as verified facts.
- AI interaction history is separated from canonical career facts.
- Consent is explicit for importing optional NPTOR learning/certification data and for AI processing.

## Initial default templates

Seed a default template library:

1. ATS Classic — recommended default for general applications.
2. Modern Professional — corporate/business.
3. Executive — senior professionals and management.
4. Technical — software, data, engineering.
5. Fresher — students and recent graduates.
6. Academic — research/education.
7. Government — public-sector applications.
8. Minimal — clean/simple presentation.

Templates should carry metadata such as name, slug, category, description, preview information, configuration, active/free flags, and sort order. Rendering should consume a normalized CV representation and template configuration.

## Existing CV import

Accept PDF and DOCX uploads. Build an extraction service with format-specific adapters and a normalized extraction result. The first implementation must support deterministic text extraction and rule-based parsing for common CV fields without requiring an external AI provider. AI enrichment can be plugged in later through a provider interface.

Every extracted field must have a review state so the UI can distinguish imported/unconfirmed information from user-confirmed information.

## AI service boundary

Keep AI behind provider/service interfaces. Planned services include:

- CV writer/rewriter
- CV reviewer
- job matcher/tailoring assistant
- career interviewer
- optional future interview preparation

AI outputs are suggestions. The application must preserve user control and should never silently fabricate employers, dates, qualifications, metrics, certifications, or achievements.

## Document generation

Use a template renderer with separate PDF and DOCX adapters. PDF is the primary visual output; DOCX is an editable alternative. Templates must be reusable and version-safe so an existing CV remains renderable even if a template changes later.

## Delivery

Use a delivery abstraction:

```text
CV Version → Document Generator → Delivery Service → Email / WhatsApp / Viber
```

Store delivery channel, document format, status, timestamps, recipient metadata needed for delivery, and error information. Email can reuse existing NPTOR account email services. WhatsApp/Viber adapters should be provider-agnostic and configurable so credentials/providers can be added without changing CV models.

## Rewards

Reward users for improving their career profile rather than selling or exposing personal information. Candidate rewards include free templates, AI credits, ATS review, or export benefits. Reward events should be auditable and idempotent.

## Privacy and security

- Users can view/edit/delete their career data and saved CVs.
- Account email remains authoritative for account communication.
- Optional learning/certification import requires user confirmation.
- Uploaded CV files and extracted content must be protected by normal authenticated ownership checks.
- AI requests should send only the minimum necessary information.
- No AI-generated factual claim becomes canonical until confirmed by the user.

## UX

The primary workspace should provide:

- My CVs
- Master Career Profile
- Create New CV
- Import Existing CV
- Template selection and live preview
- Version history
- Export/delivery actions

The collection experience is hybrid: a concise structured form establishes the profile, then the AI interviewer progressively fills gaps. A manual-only path remains available.

## Implementation boundaries

Phase 1 should establish the complete end-to-end foundation: app, models, migrations, admin, authenticated UI, profile/CV CRUD, import pipeline, default templates, preview/rendering, PDF/DOCX export, and service interfaces for AI/delivery. External AI/WhatsApp/Viber credentials must not be required to use the core CV builder.

Phase 2 can connect production AI and external messaging providers behind the established interfaces, followed by advanced ATS/job tailoring and reward automation.

## Testing

Cover model ownership and constraints, CV/profile CRUD, import normalization, confirmation state, template selection, versioning, rendering/export boundaries, and access control. Tests must prove that CV creation works without any course/exam/track enrollment.
