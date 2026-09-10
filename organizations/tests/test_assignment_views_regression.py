from django.test import SimpleTestCase

from organizations.views.admin.assignments import org_assignments


class AssignmentViewRegressionTests(SimpleTestCase):
    def test_assignment_list_source_does_not_reference_invalid_resource_access_relation(self):
        """Regression guard for the invalid select_related relation."""
        source = org_assignments.__wrapped__.__code__.co_consts
        self.assertNotIn("resource_access", source)
