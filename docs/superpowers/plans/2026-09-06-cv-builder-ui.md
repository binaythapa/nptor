# CV Builder UI

## Goal
Finish the user-facing CV Builder on top of the existing CV/profile architecture without coupling CVs to courses or exams.

## Design
- Add a dedicated builder route while retaining the existing edit route for compatibility.
- Present CV metadata and profile-backed sections in a single responsive editor.
- Let users select which master-profile records appear in the CV.
- Store section selection in `CV.selected_sections` and CV-specific text overrides in `CV.overrides`.
- Keep the master Career Profile reusable and unchanged by Builder edits.
- Provide preview, PDF, Word, and version actions from the builder.
- Enforce ownership through the existing owner-scoped CV lookup.

## Sections
- Personal/contact information
- Professional title and summary
- Work experience
- Education
- Skills
- Certifications
- Projects
- Achievements

## Validation
- Add view tests for rendering, saving Builder state, and cross-user protection.
- Run the full `cv` test suite plus `makemigrations --check` before completion.
