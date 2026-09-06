# AI Career Profile Population Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert user-confirmed AI career interview facts into the structured Master Career Profile without allowing unconfirmed or cross-user data to change trusted profile data.

**Architecture:** Keep `AIExtraction` as the audit/source record and add a focused population service that aggregates confirmed interview facts by section. A section is materialized only when its required identity fields are present; subsequent confirmed fields update the same logical record. Confirmation and profile materialization run in one database transaction.

**Tech Stack:** Django ORM, MySQL-compatible transactions, existing CareerProfile child models, existing AIConversation/AIExtraction models, Django TestCase.

**Spec:** Approved chat design: confirmed extraction → structured profile, strict confirmation, idempotency, atomic update, tests first.

## Global Constraints

- AI is never the source of truth; only user-confirmed extraction values may populate trusted profile data.
- Existing profile values must not be silently overwritten by unrelated AI extraction records.
- Population must be owner-scoped to the interview conversation.
- Re-confirming an extraction must not create duplicate child records.
- Do not add a migration unless the existing schema cannot support the feature.

---

### Task 1: Add failing service tests

**Files:**
- Modify: `cv/tests/test_career_profile.py`

**Interfaces:**
- Consumes: `confirm_interview_extraction`.
- Produces: regression coverage for materializing experience, skills, projects, education, certifications, achievements, idempotency, and required-field gating.

- [ ] **Step 1: Write tests for confirmed experience materialization.**

```python
def test_confirmed_experience_facts_materialize_profile_record(self):
    conversation = AIConversation.objects.create(owner=self.user, purpose=AIConversation.PURPOSE_INTERVIEW)
    for field_name, value in (("job_title", "Data Engineer"), ("employer", "Acme"), ("description", "Built ETL pipelines")):
        extraction = AIExtraction.objects.create(conversation=conversation, section="experience", field_name=field_name, proposed_value=value)
        self.client.post(reverse("cv:career_interview_confirm", kwargs={"pk": extraction.pk}), {"value": value})
    profile = CareerProfile.objects.get(user=self.user)
    self.assertEqual(profile.careerexperience_records.count(), 1)
    record = profile.careerexperience_records.get()
    self.assertEqual(record.job_title, "Data Engineer")
    self.assertEqual(record.employer, "Acme")
    self.assertEqual(record.description, "Built ETL pipelines")
    self.assertEqual(record.source, "ai_interview")
    self.assertTrue(record.is_confirmed)
```

- [ ] **Step 2: Add tests for each single-identity section.**

```python
def test_confirmed_skill_materializes_once(self):
    extraction = AIExtraction.objects.create(
        conversation=self.conversation,
        section="skills",
        field_name="name",
        proposed_value="Python",
    )
    self.client.post(reverse("cv:career_interview_confirm", kwargs={"pk": extraction.pk}), {"value": "Python"})
    self.client.post(reverse("cv:career_interview_confirm", kwargs={"pk": extraction.pk}), {"value": "Python"})
    self.assertEqual(CareerProfile.objects.get(user=self.user).careerskill_records.filter(name="Python").count(), 1)
```

Use the same pattern for project `name`, achievement `title`, certification `name`, and education `qualification` + `institution`.

- [ ] **Step 3: Add a test proving experience does not materialize until required identity fields exist.**

```python
def test_experience_waits_for_job_title_and_employer(self):
    extraction = AIExtraction.objects.create(
        conversation=self.conversation,
        section="experience",
        field_name="job_title",
        proposed_value="Data Engineer",
    )
    self.client.post(reverse("cv:career_interview_confirm", kwargs={"pk": extraction.pk}), {"value": "Data Engineer"})
    self.assertFalse(CareerProfile.objects.get(user=self.user).careerexperience_records.exists())
```

- [ ] **Step 4: Run the focused tests and verify they fail before implementation.**

Run: `python manage.py test cv.tests.test_career_profile -v 2`
Expected: new materialization tests fail because confirmation currently only marks the extraction confirmed.

### Task 2: Implement profile materialization service

**Files:**
- Create: `cv/services/ai/career_profile_population.py`
- Modify: `cv/services/ai/career_interviewer.py`

**Interfaces:**
- Consumes: confirmed `AIExtraction`, owning user, and all confirmed interview extractions for that conversation.
- Produces: `apply_confirmed_extraction(extraction)` and idempotent updates to CareerProfile child records.

- [ ] **Step 1: Implement normalized confirmed-value extraction.**

```python
def _confirmed_values(conversation):
    return {
        extraction.field_name: extraction.proposed_value
        for extraction in conversation.extractions.filter(confirmed=True).order_by("created_at", "id")
    }
```

- [ ] **Step 2: Implement section mappings using the existing model fields.**

Experience requires `job_title` and `employer`; education requires `institution` and `qualification`; all other sections require their identity field (`name` or `title`). Ignore unknown fields rather than writing arbitrary model attributes.

- [ ] **Step 3: Use `transaction.atomic()` around confirmation and materialization.**

```python
with transaction.atomic():
    extraction.proposed_value = value
    extraction.confirmed = True
    extraction.confirmed_by = user
    extraction.confirmed_at = timezone.now()
    extraction.save(update_fields=["proposed_value", "confirmed", "confirmed_by", "confirmed_at"])
    apply_confirmed_extraction(extraction)
```

Django guarantees that an `atomic()` block commits all changes together and rolls them back when an exception escapes the block. citeturn0search2

- [ ] **Step 4: Materialize records using deterministic identity lookups.**

Use these identities:
- experience: `job_title + employer`
- education: `institution + qualification`
- project: `name`
- skill: `name`
- achievement: `title`
- certification: `name + issuer` when issuer exists, otherwise `name`

Set `source="ai_interview"`, `is_confirmed=True`, and update only fields explicitly represented by confirmed extractions.

- [ ] **Step 5: Run focused tests and verify they pass.**

Run: `python manage.py test cv.tests.test_career_profile -v 2`
Expected: PASS.

### Task 3: Verify no schema changes and full CV regression suite

**Files:**
- No source changes expected.

- [ ] **Step 1: Run all CV tests.**

Run: `python manage.py test cv -v 2`
Expected: all existing tests plus the new population tests pass.

- [ ] **Step 2: Verify migrations.**

Run: `python manage.py makemigrations --check`
Expected: `No changes detected`.

- [ ] **Step 3: Run Django system checks.**

Run: `python manage.py check`
Expected: command completes; only the repository's existing CKEditor/MySQL backend warnings may remain.

- [ ] **Step 4: Commit the implementation.**

```bash
git add cv/services/ai/career_profile_population.py cv/services/ai/career_interviewer.py cv/tests/test_career_profile.py docs/superpowers/plans/2026-09-06-career-profile-population.md
git commit -m "feat: materialize confirmed career profile facts"
```
