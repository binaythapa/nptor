# Blue LMS Course Player Design

## Goal

Upgrade the student course-learning page into a professional, responsive LMS experience using blue as the primary brand color while preserving all existing course business logic.

## Scope

The change is limited to the course-player presentation layer and focused regression coverage:

- `templates/courses/student/course_player.html`
- `static/css/pages/course-mobile.css`
- focused course-player regression tests

No database/model changes and no changes to enrollment, lesson locking, completion, video tracking, quiz, practice, certificate, or preview business rules.

## Visual Direction

Use a professional blue palette:

- Primary: `#2563EB`
- Primary dark: `#1D4ED8`
- Navy: `#0F172A`
- Light blue: `#EFF6FF`
- Success: `#16A34A`
- Warning: `#F59E0B`
- Background: `#F8FAFC`
- Surface: `#FFFFFF`
- Border: `#E2E8F0`
- Main text: `#1E293B`
- Muted text: `#64748B`

The page should feel like a modern professional LMS without copying another product's branding.

## Layout

### Header

Provide a compact learning header with course navigation, course title, progress context, and a mobile curriculum control. Remove the rotating motivational quote because it competes with learning navigation and is not essential to the course experience.

### Curriculum Sidebar

Present sections and lessons as a structured curriculum. Show section grouping, active lesson state, completed state, and lesson-type cues. Keep the sidebar independently scrollable on desktop and transform it into an accessible slide-out drawer on smaller screens.

### Lesson Content

Use a readable content column with breadcrumb/context, prominent lesson title, optional lesson metadata, and a dedicated content surface. Preserve the existing rendering behavior for video, article, quiz, and practice lessons. Existing rich article content must remain safe and responsive.

### Progress

Show overall course completion in the sidebar/header using the existing `progress`, `completed`, and `total` context values. Preview mode must continue to show preview status and must not display personal student progress.

### Lesson Navigation

Provide clear previous/current/next navigation. Preserve the existing previous-link JavaScript behavior and `next_lesson` backend behavior. Navigation must remain usable on mobile as a sticky bottom control.

### Completion / Certificate

Preserve the existing lesson-completed state, course-completion celebration, and certificate action. Styling should make these states visually consistent with the new blue theme while keeping their existing URLs and conditions.

### Preview Mode

Keep developer/admin preview visually distinct. Preserve the existing preview banner, preview badge, disabled progress behavior, and preview-only navigation. Do not create or modify student progress from presentation changes.

## Responsive Requirements

- Desktop: persistent curriculum sidebar plus main lesson column.
- Tablet: reduced spacing and dimensions while retaining two-column navigation where practical.
- Mobile: sticky top header, slide-out curriculum drawer, full-width lesson content, and sticky previous/next navigation.
- Touch targets should be at least 44px where practical.
- Support `prefers-reduced-motion`.
- Preserve readable contrast and visible keyboard focus states.

## Accessibility Requirements

- Use semantic `header`, `aside`, `main`, and `nav` regions.
- Keep meaningful `aria-label`, `aria-controls`, and `aria-expanded` values on interactive navigation controls.
- Ensure the active lesson is visually and programmatically understandable.
- Do not rely on color alone for completed/current/locked states.
- Maintain keyboard access to the curriculum drawer and close it with Escape.

## Regression Protection

Add focused tests that verify the course-player template retains critical URLs/conditions and the new structural hooks/classes. Tests should cover:

1. Course lesson navigation still uses the course learning route.
2. Quiz and practice lesson links retain course/lesson context.
3. Preview mode still distinguishes preview links and notices.
4. Certificate rendering remains conditional on certificate context.
5. Mobile navigation hooks required by the JavaScript remain present.

## Non-Goals

- No changes to course models or migrations.
- No changes to access-control rules.
- No changes to lesson completion algorithms.
- No changes to quiz/practice execution.
- No new frontend framework or dependency.
- No database redesign.
