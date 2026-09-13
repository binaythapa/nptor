# Organization Student Profile Specification

## Goal
Provide every active organization student with a private, organization-specific profile that they can complete and maintain from their account.

## Architecture
`OrganizationMember` remains the organization boundary. Each student membership has one `OrganizationStudent` record, so the same user can have independent profiles in multiple organizations. Personal fields that are organization-specific are stored on `OrganizationStudent`; global account identity remains on the user model.

## Student lifecycle
- When an organization adds a user with the `student` role, an `OrganizationStudent` profile is created automatically if one does not already exist.
- Existing student profiles are preserved when membership is reactivated or the role is restored.
- Removing organization membership does not expose the profile to the student because profile access requires an active student membership.

## Editable profile data
Students may maintain first name, last name, date of birth, contact phone, guardian name, guardian relationship, guardian phone, guardian email, and address.

Enrollment/administrative fields such as student ID, admission number, status, joined date, class, section, and roll number remain organization-controlled.

## Access control
- Students may view/edit only their own active profile for the current organization.
- Organization administrators may view/edit profiles belonging to their organization.
- Teachers may view student profiles according to existing teacher authorization; they do not gain editing rights.
- Organization A must never expose profile data belonging to organization B.

## User experience
Student-facing organization navigation exposes `My Profile` when the current membership is a student. The profile page provides a clear completion/edit action and displays the organization name so students understand which organization's profile they are editing.

## Validation
- Contact phone and guardian phone are stored as strings to support international formats.
- Email fields use Django email validation.
- Profile creation is idempotent and keyed by `(organization, user)` through the existing `OrganizationStudent` uniqueness constraint.
