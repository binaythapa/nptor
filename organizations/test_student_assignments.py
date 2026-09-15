from unittest.mock import patch

from django.test import TestCase

from organizations.models.assignment import ResourceAssignment
from organizations.services.assignments import InvalidAssignmentError, assign_resource
from organizations.views.admin.assignments import _assignment_form_context


class OrganizationStudentAssignmentContractTests(TestCase):
    def test_student_assignment_resource_types_are_course_and_track(self):
        self.assertEqual(
            {ResourceAssignment.RESOURCE_COURSE, ResourceAssignment.RESOURCE_TRACK},
            {"course", "track"},
        )

    @patch("organizations.services.assignments._validate_actor")
    @patch("organizations.services.assignments._validate_student")
    def test_service_rejects_direct_exam_assignment(self, validate_student, validate_actor):
        organization = type("Organization", (), {"is_active": True})()
        with self.assertRaises(InvalidAssignmentError) as raised:
            assign_resource(
                student=object(),
                organization=organization,
                resource_type=ResourceAssignment.RESOURCE_EXAM,
                resource_id=1,
                actor=object(),
            )
        self.assertIn("Only Courses and Tracks", str(raised.exception))

    def test_assignment_context_does_not_build_an_exam_collection(self):
        self.assertNotIn("exams", _assignment_form_context.__code__.co_varnames)
