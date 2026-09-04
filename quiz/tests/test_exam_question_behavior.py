from pathlib import Path
import unittest


class ExamQuestionBehaviorTests(unittest.TestCase):
    def test_exam_question_uses_stable_choice_order_for_an_attempt(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / "quiz" / "views" / "exams.py").read_text(encoding="utf-8")
        self.assertIn('random.Random(f"{ue.id}:{q.id}").shuffle(choices)', source)
        self.assertNotIn("random.shuffle(choices)", source)

    def test_exam_question_has_a_single_explicit_option_marker_path(self):
        root = Path(__file__).resolve().parents[2]
        template = (root / "templates" / "quiz" / "student" / "exam" / "exam_question.html").read_text(encoding="utf-8")
        self.assertIn('forloop.counter == 1', template)
        self.assertIn('forloop.counter == 2', template)
        self.assertIn('forloop.counter == 3', template)
        self.assertIn('forloop.counter == 4', template)


if __name__ == "__main__":
    unittest.main()
