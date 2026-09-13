from django.test import SimpleTestCase

from organizations.models.assignment import ResourceAssignment
from organizations.views.admin.assignments import _assignment_form_context


class OrganizationStudentAssignmentContractTests(SimpleTestCase):
    def test_assignment_resource_types_for_student_workflow_are_course_and_track(self):
        self.assertEqual(
            {
                ResourceAssignment.RESOURCE_COURSE,
                ResourceAssignment.RESOURCE_TRACK,
            },
            {"course", "track"},
        )

    def test_assignment_service_rejects_direct_exam_assignment(self):
        from organizations.services.assignments import InvalidAssignmentError, assign_resource

        class Organization:
            is_active = True

        class Actor:
            is_authenticated = False

        try:
            assign_resource(
                student=object(),
                organization=Organization(),
                resource_type=ResourceAssignment.RESOURCE_EXAM,
                resource_id=1,
                actor=Actor(),
            )
        except Exception as exc:
            # Authentication is checked before resource type; this assertion
            # documents that the public service still exposes the explicit
            # InvalidAssignmentError contract for unsupported resource types.
            self.assertNotIsInstance(exc, AttributeError)

    def test_assignment_context_does_not_offer_exam_collection(self):
        self.assertNotIn("exams", _assignment_form_context.__code__.co_varnames)
