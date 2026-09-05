# Certificate Verification Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the existing NPTOR public certificate verification experience into a professional, blue-branded verification page while preserving certificate data and verification behavior.

**Architecture:** Reuse the existing `CourseCertificate` model and course relationships. Add a public certificate verification view/URL only if the current repository does not contain the deployed verification route, and render a focused verification template with dedicated CSS; do not add database fields or alter certificate issuance logic. The verification page will present authenticity, learner/course metadata, completion sections, and sharing/download actions using existing routes where safely available.

**Tech Stack:** Django views/URLs/templates, CSS3, existing `CourseCertificate` and `Course` models, Django TestCase/SimpleTestCase.

**Spec:** Approved in conversation on 2026-09-05; visual reference is the supplied NPTOR certificate verification screenshots.

## Global Constraints

- Preserve the existing `CourseCertificate` data model and issuance algorithm.
- Do not change course completion, enrollment, subscription, quiz, or practice business rules.
- Verification must be publicly accessible by certificate ID and must not require student login.
- Use the NPTOR blue LMS palette: primary `#2563EB`, primary dark `#1D4ED8`, navy `#0F172A`, soft blue `#EFF6FF`, success `#16A34A`, background `#F8FAFC`, surface `#FFFFFF`, border `#E2E8F0`, text `#1E293B`, muted `#64748B`.
- Keep certificate ID, learner, course, issue date, and completion information truthful to stored data.
- Do not invent certificate claims such as vendor accreditation or endorsement.
- Make verification status understandable without relying on color alone.
- Provide responsive mobile behavior, visible focus states, keyboard-accessible controls, and touch targets of at least 44px.

---

### Task 1: Protect the Verification Page Contract

**Files:**
- Create: `courses/test_certificate_verification.py`
- Modify: `courses/urls.py` only if a public verification route is absent
- Modify: `courses/views/student_views.py` only if a public verification view is absent

**Interfaces:**
- Consumes: `CourseCertificate.certificate_id` and related `user`, `course`, and course sections.
- Produces: public named URL `courses:certificate_verify` and template context containing the certificate and its course/learner data.

- [ ] **Step 1: Write the failing contract test**

```python
from pathlib import Path

from django.test import SimpleTestCase


class CertificateVerificationTemplateContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = (
            Path(__file__).resolve().parent.parent
            / "templates"
            / "courses"
            / "student"
            / "certificate_verification.html"
        ).read_text(encoding="utf-8")

    def test_verification_hierarchy_exists(self):
        for hook in (
            'class="certificate-verification-page"',
            'class="certificate-status"',
            'class="certificate-details"',
            'class="certificate-completion"',
            'class="certificate-actions"',
        ):
            self.assertIn(hook, self.template)

    def test_verification_data_fields_are_preserved(self):
        for hook in (
            "certificate.certificate_id",
            "certificate.user",
            "certificate.course",
            "certificate.issued_at",
        ):
            self.assertIn(hook, self.template)

    def test_public_verification_route_is_named(self):
        from django.urls import reverse

        self.assertEqual(
            reverse("courses:certificate_verify", args=["CERT-TEST"]),
            "/courses/certificate/CERT-TEST/",
        )
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `python manage.py test courses.test_certificate_verification -v 2`
Expected: FAIL because the verification template and/or named route does not yet exist in the current repository.

- [ ] **Step 3: Add the minimal public verification endpoint**

If the current repository has no equivalent endpoint, add a view using the existing certificate model:

```python
from courses.models import CourseCertificate


def certificate_verify(request, certificate_id):
    certificate = get_object_or_404(
        CourseCertificate.objects.select_related("user", "course"),
        certificate_id=certificate_id,
    )
    sections = certificate.course.sections.prefetch_related("lessons").order_by("order")
    return render(
        request,
        "courses/student/certificate_verification.html",
        {
            "certificate": certificate,
            "sections": sections,
        },
    )
```

Add the route before the generic course slug route:

```python
path(
    "certificate/<str:certificate_id>/",
    student_views.certificate_verify,
    name="certificate_verify",
),
```

- [ ] **Step 4: Run the focused test again**

Run: `python manage.py test courses.test_certificate_verification -v 2`
Expected: the URL/view contract progresses to template assertions; the implementation then supplies the template in Task 2.

- [ ] **Step 5: Commit the endpoint contract**

```bash
git add courses/test_certificate_verification.py courses/urls.py courses/views/student_views.py
git commit -m "feat: add public certificate verification endpoint"
```

---

### Task 2: Build the Blue Verification Experience

**Files:**
- Create: `templates/courses/student/certificate_verification.html`
- Create: `static/css/pages/certificate-verification.css`
- Modify: `courses/test_certificate_verification.py`

**Interfaces:**
- Consumes: `certificate`, `sections` from Task 1.
- Produces: responsive public verification UI with stable semantic hooks for future tests and styling.

- [ ] **Step 1: Extend the failing test with the required UI hooks**

```python
def test_verification_has_status_metadata_and_actions(self):
    for hook in (
        "Verified Certificate",
        "Officially issued by NPTOR",
        "Student",
        "Course",
        "Certificate ID",
        "Issued on",
        "Course Completion",
        "Download Certificate",
        "Share on LinkedIn",
        "Share on WhatsApp",
        "certificate_id",
    ):
        self.assertIn(hook, self.template)
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `python manage.py test courses.test_certificate_verification -v 2`
Expected: FAIL until the new template contains the required hierarchy and actions.

- [ ] **Step 3: Implement the template**

Use a semantic structure equivalent to:

```html
<main class="certificate-verification-page">
  <section class="certificate-shell" aria-labelledby="verification-title">
    <header class="certificate-hero">
      <img src="{% static 'images/logo.png' %}" alt="NPTOR">
      <span class="verified-seal" aria-hidden="true">✓</span>
      <span class="certificate-status">Verified Certificate</span>
      <p>Officially issued by NPTOR</p>
      <h1 id="verification-title">Certificate Verification</h1>
    </header>

    <section class="certificate-details" aria-label="Certificate details">
      <div><span>Student</span><strong>{{ certificate.user.get_full_name|default:certificate.user.username }}</strong></div>
      <div><span>Course</span><strong>{{ certificate.course.title }}</strong></div>
      <div><span>Certificate ID</span><strong>{{ certificate.certificate_id }}</strong></div>
      <div><span>Issued on</span><strong>{{ certificate.issued_at|date:"d F Y" }}</strong></div>
    </section>

    <section class="certificate-completion" aria-labelledby="completion-title">
      <div class="section-heading">
        <span>COURSE COMPLETION</span>
        <h2 id="completion-title">Completed curriculum</h2>
      </div>
      {% for section in sections %}
        <div class="completion-row">
          <span aria-hidden="true">✓</span>
          <span>Section {{ forloop.counter }}: {{ section.title }}</span>
        </div>
      {% endfor %}
    </section>

    <p class="verification-note">✓ This certificate has been verified through the NPTOR certificate verification system.</p>

    <section class="certificate-actions" aria-label="Certificate actions">
      <a href="{% url 'courses:course_certificate_pdf' certificate.course.slug %}" class="btn-primary">Download Certificate</a>
      <a href="https://www.linkedin.com/sharing/share-offsite/?url={{ request.build_absolute_uri }}" class="btn-secondary">Share on LinkedIn</a>
      <a href="https://wa.me/?text={{ request.build_absolute_uri|urlencode }}" class="btn-success">Share on WhatsApp</a>
    </section>
  </section>
</main>
```

The final implementation must use `{% load static %}` and may use Django-safe URL encoding/filtering as needed. Do not claim vendor certification; this page verifies an NPTOR course-completion certificate only.

- [ ] **Step 4: Add responsive blue styling**

Define the same LMS tokens used by the course player and style the page as a centered white certificate surface on `#F8FAFC`, with a navy/blue verification hero, structured metadata rows, completion checklist, and responsive action buttons.

```css
.certificate-verification-page {
  min-height: 100vh;
  padding: 40px 20px;
  background: var(--lms-bg, #f8fafc);
  color: var(--lms-text, #1e293b);
  font-family: Inter, ui-sans-serif, system-ui, sans-serif;
}

.certificate-shell {
  width: min(960px, 100%);
  margin: 0 auto;
  padding: clamp(24px, 5vw, 52px);
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(15, 23, 42, .08);
}

.certificate-status {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  padding: 0 14px;
  border-radius: 999px;
  background: #f0fdf4;
  color: #166534;
  font-weight: 800;
}

.certificate-details,
.certificate-completion {
  margin-top: 28px;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  overflow: hidden;
}

.certificate-details > div,
.completion-row {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding: 17px 20px;
  border-bottom: 1px solid #e2e8f0;
}

.certificate-details > div:last-child,
.completion-row:last-child { border-bottom: 0; }

.certificate-details span { color: #64748b; }
.certificate-details strong { color: #0f172a; text-align: right; }

.certificate-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  margin-top: 30px;
}

@media (max-width: 640px) {
  .certificate-verification-page { padding: 14px 10px; }
  .certificate-shell { padding: 24px 16px; border-radius: 14px; }
  .certificate-details > div { align-items: flex-start; flex-direction: column; gap: 5px; }
  .certificate-details strong { text-align: left; }
  .certificate-actions > a { width: 100%; }
}
```

- [ ] **Step 5: Run the focused test to verify it passes**

Run: `python manage.py test courses.test_certificate_verification -v 2`
Expected: PASS.

- [ ] **Step 6: Commit the verification UI**

```bash
git add courses/test_certificate_verification.py templates/courses/student/certificate_verification.html static/css/pages/certificate-verification.css
git commit -m "feat: redesign certificate verification page"
```

---

### Task 3: Verify Safety, Navigation, and Existing Certificate Behavior

**Files:**
- Modify: `courses/test_certificate_verification.py` if additional regression coverage is required.
- Inspect: `courses/services/certificate_pdf.py`, `courses/services/certificates.py`, `courses/models/certificate.py`, `courses/urls.py`.

- [ ] **Step 1: Add a test for unknown certificate IDs**

```python
def test_unknown_certificate_id_returns_not_found(self):
    response = self.client.get("/courses/certificate/DOES-NOT-EXIST/")
    self.assertEqual(response.status_code, 404)
```

- [ ] **Step 2: Run the focused certificate tests**

Run: `python manage.py test courses.test_certificate_verification -v 2`
Expected: PASS.

- [ ] **Step 3: Inspect the certificate PDF link**

Confirm the verification page does not expose an invented or unrelated URL. If the existing PDF endpoint requires entitlement/login, do not silently weaken that authorization in this UI-only task; leave the action pointing to the existing certificate PDF endpoint and record that public PDF delivery is a separate security-reviewed enhancement.

- [ ] **Step 4: Run the strongest available course test subset**

Run: `python manage.py test courses -v 2`
Expected: PASS in a fully configured local environment. If the environment cannot run Django/database tests, report the exact limitation rather than claiming success.

- [ ] **Step 5: Inspect the final diff**

Confirm only the intended certificate verification files/routes/tests changed and that certificate issuance, course completion, and entitlement logic were not modified.

- [ ] **Step 6: Commit any test-only correction**

```bash
git add courses/test_certificate_verification.py
git commit -m "test: strengthen certificate verification coverage"
```

---

### Task 4: Final Repository Verification

**Files:**
- No new files unless verification discovers a concrete defect.

- [ ] **Step 1: Confirm the latest commit and changed paths**

Inspect the latest GitHub commit and compare it with its parent.

- [ ] **Step 2: Confirm there are no model or migration changes**

The certificate redesign must remain schema-neutral.

- [ ] **Step 3: Confirm the public URL**

The expected verification URL is:

```text
/courses/certificate/<certificate_id>/
```

- [ ] **Step 4: Record test evidence**

Report exactly which Django tests were executed and their result. If local execution is unavailable, explicitly state that browser/runtime validation remains to be performed on the user's environment.

- [ ] **Step 5: Provide the final commit SHA and manual smoke-test checklist**

Manual checks:

1. Open a known certificate ID.
2. Confirm `Verified Certificate` and `Officially issued by NPTOR` are visible.
3. Confirm learner/course/ID/date match the certificate record.
4. Confirm every course section appears in completion history.
5. Confirm unknown IDs return 404.
6. Confirm mobile layout is readable and action buttons are usable.
7. Confirm existing certificate PDF and sharing actions behave as expected.
