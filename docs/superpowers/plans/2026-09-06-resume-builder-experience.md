# Resume Builder Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing NPTOR CV builder into a responsive, autosaving, AI-assisted, job-targeted resume workspace without replacing the existing Django rendering/export architecture.

**Architecture:** Keep `CareerProfile` as the master source and `CV` as the independent resume layer. Store per-CV job targeting inside the existing `overrides` JSON field, add small owner-scoped JSON endpoints for autosave/AI/ATS, and keep the canonical preview renderer in Django by reloading its iframe after saves.

**Tech Stack:** Django 6, server-rendered templates, Bulma classes already used by NPTOR, vanilla JavaScript/fetch, existing provider abstraction, Django TestCase.

**Spec:** `docs/superpowers/specs/2026-09-06-resume-builder-experience-design.md`

## Global Constraints

- Do not copy Resume Now branding, proprietary source code, or exact visual design.
- Keep Career Profile as the master data source; CV changes must remain CV-specific.
- AI suggestions must not be silently persisted and must follow the existing truthfulness rule.
- Preserve existing CV routes, preview, versions, import, interview, AI review, ATS, tailoring, PDF, and DOCX behavior.
- Do not introduce a frontend framework or new build pipeline.

---

### Task 1: Add builder state and AI service tests

**Files:**
- Modify: `cv/tests/test_ai_services.py`
- Create: `cv/tests/test_builder_workspace.py`

**Interfaces:**
- Tests will define the expected `CV` override shape: `overrides["target_job"]` containing `title`, `company`, and `description`.
- Tests will define `POST /cv/<id>/builder/autosave/`, `POST /cv/<id>/builder/ai/`, and `POST /cv/<id>/builder/ats/` behavior.

- [ ] **Step 1: Write failing tests for target job persistence and owner isolation**

```python
class BuilderWorkspaceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="builder", password="pass")
        self.other = get_user_model().objects.create_user(username="other", password="pass")
        self.profile = CareerProfile.objects.create(user=self.user)
        self.template = CVTemplate.objects.create(name="Test", slug="builder-test", is_active=True)
        self.cv = CV.objects.create(owner=self.user, profile=self.profile, template=self.template, title="Target CV")

    def test_autosave_persists_target_job_and_profile_fields(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("cv:cv_builder_autosave", args=[self.cv.pk]),
            data=json.dumps({
                "title": "Data Engineer - ACME",
                "professional_title": "Data Engineer",
                "summary": "Snowflake and Python engineer",
                "target_job": {
                    "title": "Senior Data Engineer",
                    "company": "ACME",
                    "description": "Snowflake Python AWS",
                },
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.cv.refresh_from_db()
        self.assertEqual(self.cv.overrides["target_job"]["company"], "ACME")
        self.assertEqual(self.cv.overrides["summary"], "Snowflake and Python engineer")

    def test_autosave_cannot_modify_another_users_cv(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("cv:cv_builder_autosave", args=[self.cv.pk]),
            data=json.dumps({"title": "Hacked"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
```

- [ ] **Step 2: Run the focused test and verify it fails because the endpoint is absent**

Run: `python manage.py test cv.tests.test_builder_workspace.BuilderWorkspaceTests.test_autosave_persists_target_job_and_profile_fields -v 2`

Expected: FAIL because `cv:cv_builder_autosave` does not exist yet.

- [ ] **Step 3: Add failing service tests for skill suggestions**

```python
def test_suggest_skills_returns_unconfirmed_suggestion(self):
    result = suggest_skills(
        {"professional_title": "Data Engineer", "skills": ["Python"]},
        "Senior Data Engineer",
        provider=self.provider,
    )
    self.assertFalse(result["confirmed"])
    self.assertIn("skills", result)
```

- [ ] **Step 4: Run the focused service test and verify it fails because `suggest_skills` is absent**

Run: `python manage.py test cv.tests.test_ai_services.AIServicesTests.test_suggest_skills_returns_unconfirmed_suggestion -v 2`

Expected: FAIL with an import/name error for `suggest_skills`.

### Task 2: Implement provider-backed builder AI actions

**Files:**
- Modify: `cv/services/ai/cv_writer.py`
- Modify: `cv/services/ai/schemas.py` only if structured skill output is needed by the provider
- Modify: `cv/tests/test_ai_services.py`

**Interfaces:**
- `suggest_skills(cv_payload, target_job_title, provider=None) -> dict`
- Returned dict contains `skills`, `source`, and `confirmed=False`.

- [ ] **Step 1: Implement the minimal `suggest_skills` service**

```python
def suggest_skills(cv_payload, target_job_title, provider=None):
    provider = provider or get_ai_provider()
    prompt = (
        f"{TRUTH_RULE}\nSuggest relevant resume skills for the target role. "
        f"Only select skills supported by the supplied CV data or clearly implied by existing skills. "
        f"Target role: {target_job_title}\nCV data: {cv_payload}"
    )
    text = provider.generate_text(prompt, system_prompt=TRUTH_RULE)
    skills = [item.strip(" -*") for item in text.splitlines() if item.strip()]
    return {"skills": skills[:12], "source": "ai_suggestion", "confirmed": False}
```

- [ ] **Step 2: Run the service tests and verify they pass**

Run: `python manage.py test cv.tests.test_ai_services.AIServicesTests.test_suggest_skills_returns_unconfirmed_suggestion -v 2`

Expected: PASS.

### Task 3: Add owner-scoped builder JSON endpoints

**Files:**
- Modify: `cv/views.py`
- Modify: `cv/urls.py`
- Create: `cv/services/cv_workspace.py`
- Modify: `cv/tests/test_builder_workspace.py`

**Interfaces:**
- `POST cv_builder_autosave(request, pk)` accepts JSON with `title`, `status`, `template_id`, `professional_title`, `summary`, `linkedin_url`, `portfolio_url`, `target_job`, and `selected_sections` and returns `{ok: true, updated_at: ...}`.
- `POST cv_builder_ai(request, pk)` accepts `action` (`summary`, `bullet`, or `skills`) and returns an unpersisted suggestion payload.
- `POST cv_builder_ats(request, pk)` accepts optional `job_description`, calls `analyze_ats`, and returns score/results as JSON.
- `cv/services/cv_workspace.py` owns normalization of target-job and selected-section payloads so views stay small.

- [ ] **Step 1: Write failing tests for AI endpoint and ATS endpoint**

```python
def test_ai_summary_endpoint_returns_unconfirmed_suggestion(self):
    self.client.force_login(self.user)
    set_provider_for_tests(FakeProvider())
    response = self.client.post(
        reverse("cv:cv_builder_ai", args=[self.cv.pk]),
        data=json.dumps({"action": "summary"}),
        content_type="application/json",
    )
    self.assertEqual(response.status_code, 200)
    self.assertFalse(response.json()["suggestion"]["confirmed"])


def test_ats_endpoint_uses_target_job_description(self):
    self.client.force_login(self.user)
    set_provider_for_tests(FakeProvider())
    response = self.client.post(
        reverse("cv:cv_builder_ats", args=[self.cv.pk]),
        data=json.dumps({"job_description": "Need Python and Kubernetes"}),
        content_type="application/json",
    )
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.json()["analysis"]["score"], 76)
```

- [ ] **Step 2: Run the focused endpoint tests and verify they fail because the URLs are absent**

Run: `python manage.py test cv.tests.test_builder_workspace.BuilderWorkspaceTests.test_ai_summary_endpoint_returns_unconfirmed_suggestion cv.tests.test_builder_workspace.BuilderWorkspaceTests.test_ats_endpoint_uses_target_job_description -v 2`

Expected: FAIL with URL resolution errors.

- [ ] **Step 3: Implement `cv_workspace.py` normalization helpers**

```python
def normalize_target_job(value):
    value = value if isinstance(value, dict) else {}
    return {
        "title": str(value.get("title", ""))[:255],
        "company": str(value.get("company", ""))[:255],
        "description": str(value.get("description", ""))[:12000],
    }


def normalize_selected_sections(value):
    if not isinstance(value, dict):
        return {}
    normalized = {}
    for section, values in value.items():
        if isinstance(values, list):
            normalized[section] = [int(item) for item in values if str(item).isdigit()]
    return normalized
```

- [ ] **Step 4: Implement the three views with JSON parsing, owner filtering, and explicit action validation**

- [ ] **Step 5: Add URL patterns and run the focused endpoint tests**

Run: `python manage.py test cv.tests.test_builder_workspace -v 2`

Expected: all builder workspace endpoint tests PASS.

### Task 4: Replace the builder presentation with the responsive workspace

**Files:**
- Modify: `templates/cv/builder.html`
- Create: `static/cv/builder.css`
- Create: `static/cv/builder.js`

**Interfaces:**
- Template exposes JSON-safe initial builder state through `data-*` attributes/JSON script.
- JavaScript uses the three endpoints from Task 3 and updates `#cv-preview-frame` after successful autosave.

- [ ] **Step 1: Add the failing template assertion**

```python
def test_builder_renders_workspace_panels(self):
    self.client.force_login(self.user)
    response = self.client.get(reverse("cv:cv_builder", args=[self.cv.pk]))
    self.assertContains(response, 'data-builder-workspace="true"')
    self.assertContains(response, 'id="cv-preview-frame"')
    self.assertContains(response, "Target job")
```

- [ ] **Step 2: Run the template test and verify the current builder fails the assertions**

Run: `python manage.py test cv.tests.test_builder_workspace.BuilderWorkspaceTests.test_builder_renders_workspace_panels -v 2`

Expected: FAIL because the current template does not expose the new workspace markers.

- [ ] **Step 3: Implement the three-area responsive builder**

The template must contain:
- left section navigation with buttons that scroll/focus editor sections;
- center editor for settings, summary, experience, education, skills, projects, certifications, achievements, and target job;
- right sticky preview iframe using `{% url 'cv:cv_preview' cv.pk %}`;
- AI action buttons beside summary/experience/skills;
- save-status indicator;
- ATS result card;
- existing Review/Versions/PDF/Word/Tailor actions.

- [ ] **Step 4: Implement debounced autosave in `builder.js`**

Use a 700ms debounce after input changes. Serialize the visible form into JSON, including selected record order by DOM order. Set status to Saving before fetch, Saved after a 2xx response, and Error on failure.

- [ ] **Step 5: Implement explicit AI apply/dismiss controls**

AI responses populate a suggestion card. Clicking Apply writes the suggestion into the relevant editor field but does not directly persist it; the normal autosave path persists it.

- [ ] **Step 6: Implement target-job ATS action**

Use the target-job description from the form, call the ATS endpoint, and render score/missing keywords/recommendations without navigating away.

- [ ] **Step 7: Run the builder template tests**

Run: `python manage.py test cv.tests.test_builder_workspace -v 2`

Expected: PASS.

### Task 5: Verify regressions and commit the feature

**Files:**
- Modify: `cv/tests/test_ai_services.py` only if regression coverage needs adjustment.

- [ ] **Step 1: Run the complete CV test suite**

Run: `python manage.py test cv -v 2`

Expected: all existing and new CV tests PASS. If the environment cannot connect to its configured MySQL database, record that limitation rather than claiming the suite passed.

- [ ] **Step 2: Review the diff for accidental scope expansion**

Check that no billing, subscription, or unrelated app files changed and that all mutations remain owner-scoped.

- [ ] **Step 3: Commit the implementation**

```bash
git add cv/services/ai/cv_writer.py cv/services/cv_workspace.py cv/views.py cv/urls.py cv/tests/test_ai_services.py cv/tests/test_builder_workspace.py templates/cv/builder.html static/cv/builder.css static/cv/builder.js docs/superpowers/specs/2026-09-06-resume-builder-experience-design.md docs/superpowers/plans/2026-09-06-resume-builder-experience.md
git commit -m "feat: upgrade CV builder workspace"
```
