from types import SimpleNamespace
import unittest

from quiz.services.access import can_access_exam


class FreeExamAccessTests(unittest.TestCase):
    def test_free_exam_is_accessible_without_subscription_even_when_on_dynamic_track(self):
        user = SimpleNamespace(
            is_authenticated=True,
            id=1,
        )
        exam = SimpleNamespace(
            is_published=True,
            is_free=True,
        )

        allowed, reason = can_access_exam(user, exam)

        self.assertTrue(allowed)
        self.assertIsNone(reason)


if __name__ == "__main__":
    unittest.main()
