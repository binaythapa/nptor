from django.test import SimpleTestCase

from .models import Exam


class ExamCommerceContractTests(SimpleTestCase):
    def test_exam_has_no_individual_subscription_plan_relationship(self):
        field_names = {field.name for field in Exam._meta.get_fields()}
        self.assertNotIn("subscription_plans", field_names)
