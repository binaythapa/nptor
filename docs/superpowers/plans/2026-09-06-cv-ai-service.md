# CV AI Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Add a provider-neutral AI layer to the standalone NPTOR CV service, with OpenAI as the first optional provider, persistent conversations/extractions, safe CV writing/review/job tailoring, and delivery interfaces.

**Architecture:** AI is isolated behind `AIProvider`; OpenAI uses the Responses API only when configured. AI outputs are suggestions/proposed facts and never silently become canonical career data. Delivery uses provider-neutral adapters and auditable delivery records.

**Tech Stack:** Django 6.0, MySQL, existing `requests` dependency, Django email backend, JSONField, existing CV version/artifact services.

**Spec:** `docs/superpowers/specs/2026-09-06-cv-service-design.md`

## Global Constraints

- Core CV creation works without an AI API key.
- OpenAI is optional and isolated behind `AIProvider`.
- AI never invents employers, dates, qualifications, metrics, certifications, or achievements.
- AI-generated/extracted facts remain unconfirmed until explicit user confirmation.
- AI receives only the minimum data required for each operation.
- User ownership protects conversations, extractions, analyses, artifacts, and deliveries.
- Account email remains authoritative for email delivery.
- WhatsApp/Viber require no credentials for the core CV builder and return a controlled not-configured result when absent.

### Task 1: AI persistence

**Create:** `cv/models_ai.py`, `cv/migrations/0007_ai_models.py`, `cv/tests/test_ai_models.py`.
**Modify:** `cv/models.py`, `cv/admin.py`.

- [ ] Write failing tests for conversation/message relationships, ownership, unconfirmed AI extraction, and ATS analysis ownership.
- [ ] Implement `AIConversation`, `AIMessage`, `AIExtraction`, and `ATSAnalysis` with timestamps, indexes, JSON payloads, and explicit confirmation state.
- [ ] Re-export/register models and add migration.
- [ ] Run focused tests.
- [ ] Commit `feat: add CV AI persistence models`.

### Task 2: Provider abstraction and OpenAI adapter

**Create:** `cv/services/ai/provider.py`, `cv/services/ai/openai_provider.py`, `cv/services/ai/schemas.py`, `cv/tests/test_ai_provider.py`.
**Modify:** `objective_exam/settings.py`.

Interfaces:
- `AIProvider.generate_text(prompt, *, system_prompt="", model=None) -> str`
- `AIProvider.generate_structured(prompt, schema, *, system_prompt="", model=None) -> dict`
- `get_ai_provider() -> AIProvider`

- [ ] Write failing provider/configuration tests.
- [ ] Implement `AIProviderNotConfigured` and safe provider factory.
- [ ] Implement optional OpenAI Responses API adapter using existing `requests`; no mandatory AI SDK dependency.
- [ ] Add environment-driven `OPENAI_API_KEY` and configurable model settings without committing secrets.
- [ ] Run tests and commit `feat: add provider-neutral CV AI layer`.

### Task 3: AI CV services

**Create:** `cv/services/ai/cv_writer.py`, `cv/services/ai/cv_reviewer.py`, `cv/services/ai/career_interviewer.py`, `cv/services/ai/job_matcher.py`, `cv/tests/test_ai_services.py`.

Interfaces:
- `suggest_summary(cv_payload, provider=None) -> dict`
- `rewrite_bullet(bullet, context, provider=None) -> dict`
- `review_cv(cv_version, provider=None) -> ATSAnalysis`
- `interview_turn(conversation, user_message, provider=None) -> dict`
- `match_job(cv_payload, job_description, provider=None) -> dict`

- [ ] Write failing tests proving provider-disabled operation does not mutate canonical profile data.
- [ ] Implement truth-constrained prompts and structured result handling.
- [ ] Store interviewer proposed facts as unconfirmed `AIExtraction` records.
- [ ] Keep writer/reviewer/job matcher suggestion-only.
- [ ] Tie review results to immutable CV versions.
- [ ] Run tests and commit `feat: add CV AI assistance services`.

### Task 4: Delivery abstraction

**Create:** `cv/models_delivery.py`, `cv/migrations/0008_delivery.py`, `cv/services/delivery/base.py`, `cv/services/delivery/email.py`, `cv/services/delivery/whatsapp.py`, `cv/services/delivery/viber.py`, `cv/tests/test_delivery.py`.
**Modify:** `cv/models.py`, `cv/admin.py`.

- [ ] Write failing tests for ownership, authoritative account email, delivery status, and disabled external providers.
- [ ] Implement `DeliveryRecord` and `DeliveryProvider.send(artifact, recipient, metadata=None)`.
- [ ] Implement email through the existing Django email backend.
- [ ] Implement controlled `DeliveryNotConfigured` results for WhatsApp/Viber.
- [ ] Run tests and commit `feat: add CV delivery providers`.

### Task 5: Final verification

- [ ] Run `python manage.py makemigrations --check`.
- [ ] Run `python manage.py test cv -v 2`.
- [ ] Confirm all CV tests remain green without AI credentials.
- [ ] Confirm no provider secrets are committed.
- [ ] Fast-forward the verified implementation into `main`.
