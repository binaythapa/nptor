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

    def test_exam_question_styles_load_after_legacy_exam_styles(self):
        root = Path(__file__).resolve().parents[2]
        base = (root / "templates" / "layouts" / "student" / "base.html").read_text(encoding="utf-8")
        timer_pos = base.index("css/exam_timer.css")
        page_css_pos = base.index("{% block page_css %}")
        self.assertLess(timer_pos, page_css_pos)

    def test_exam_question_marker_cannot_stretch_with_legacy_option_span_rule(self):
        root = Path(__file__).resolve().parents[2]
        css = (root / "static" / "css" / "pages" / "exam-question.css").read_text(encoding="utf-8")
        self.assertIn(".exam-question-page .option-label span.option-marker", css)
        self.assertIn("flex: 0 0 32px", css)
        self.assertIn("width: 32px", css)
        self.assertIn("height: 32px", css)


if __name__ == "__main__":
    unittest.main()
