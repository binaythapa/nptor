# AI Career Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe AI Career Interview and make the existing CV upload a first-class entry point into the reusable Master Career Profile.

**Architecture:** Reuse `AIConversation`, `AIMessage`, and `AIExtraction` for an owner-scoped interview independent of a CV. Add a provider method that returns a conservative reply plus proposed facts, persist those facts as unconfirmed extractions, and require explicit user confirmation before profile data is trusted. Surface upload/interview/manual entry from the career profile hub.

**Tech Stack:** Django, existing CV models/services, existing OpenAI-compatible provider, Django templates, Django TestCase.

**Spec:** `docs/superpowers/specs/2026-09-06-ai-career-profile-design.md`

## Global Constraints

- AI never writes unconfirmed facts directly into `CareerProfile` or its child records.
- Interview conversations and extractions are owner-scoped.
- Existing PDF/DOCX upload validation and 10 MB limit remain in force.
- Provider output must be strict JSON and invalid output must not create extractions.
- Tests must be written before production code for each behavior.

---

### Task 1: Interview provider contract

**Files:**
- Modify: `cv/services/cv_ai.py`
- Test: `cv/tests/test_ai_services.py`

**Interfaces:**
- Produces `OpenAIProvider.interview(payload, messages)` returning `{reply, complete, extractions}`.
- Produces `start_career_interview(user, message, provider=None)` and `confirm_interview_extraction(extraction_id, user, value)`.

- [ ] **Step 1: Write failing tests** for provider interview JSON handling, persisted unconfirmed extraction, and invalid provider output.
- [ ] **Step 2: Run the focused tests and verify they fail because the interview service is absent.**
- [ ] **Step 3: Implement the smallest provider/service contract using existing `AIConversation`, `AIMessage`, and `AIExtraction`.
- [ ] **Step 4: Run the focused tests and verify they pass.**
- [ ] **Step 5: Commit the provider/service changes.**

### Task 2: Interview UI and confirmation

**Files:**
- Modify: `cv/urls.py`
- Modify: `cv/views.py`
- Create: `cv/templates/cv/career_profile.html`
- Create: `cv/templates/cv/career_interview.html`
- Test: `cv/tests/test_career_profile.py`

**Interfaces:**
- `/cv/profile/` remains the manual editor.
- Add `/cv/profile/interview/` for the interview turn flow.
- Add `/cv/profile/interview/extraction/<pk>/confirm/` for explicit confirmation.

- [ ] **Step 1: Write failing view tests for authenticated access, interview turn persistence, extraction confirmation, and cross-user rejection.**
- [ ] **Step 2: Run the focused tests and verify they fail.**
- [ ] **Step 3: Implement owner-scoped views and templates.**
- [ ] **Step 4: Run focused tests and verify they pass.**
- [ ] **Step 5: Commit the UI changes.**

### Task 3: Career Profile hub and upload entry point

**Files:**
- Modify: `cv/views.py`
- Modify: `cv/templates/cv/dashboard.html`
- Create: `cv/templates/cv/import.html`
- Create: `cv/templates/cv/import_review.html`
- Test: `cv/tests/test_career_profile.py`

**Interfaces:**
- Dashboard links to manual profile, AI interview, and existing CV upload.
- Existing `cv_import` and `cv_import_review` behavior is retained and made discoverable.

- [ ] **Step 1: Write failing tests proving the dashboard exposes the three profile entry points.**
- [ ] **Step 2: Run the focused tests and verify failure.**
- [ ] **Step 3: Implement the hub copy and upload/review templates without changing the importer semantics.**
- [ ] **Step 4: Run focused tests and verify pass.**
- [ ] **Step 5: Commit the hub changes.**

### Task 4: Full CV regression verification

**Files:**
- Test: existing `cv/tests/*`

- [ ] **Step 1: Run `python manage.py test cv -v 2`.**
- [ ] **Step 2: Run `python manage.py makemigrations --check`.**
- [ ] **Step 3: Run `python manage.py check`.**
- [ ] **Step 4: Inspect the resulting diff and confirm no unconfirmed AI extraction is treated as trusted profile data.**
- [ ] **Step 5: Commit any required migration or regression fix.**
