from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from quiz.views.exams import exam_question


class ExamChoiceOrderTests(SimpleTestCase):
    def test_choice_order_is_stable_for_same_attempt_and_question(self):
        request = RequestFactory().get("/quiz/exam/attempt/41/question/0/")
        request.user = SimpleNamespace(is_authenticated=True)
        request.session = {}

        choices = [
            SimpleNamespace(id=1),
            SimpleNamespace(id=2),
            SimpleNamespace(id=3),
            SimpleNamespace(id=4),
            SimpleNamespace(id=5),
        ]
        question = SimpleNamespace(
            id=7,
            question_type="single",
            choices=SimpleNamespace(all=lambda: choices),
        )
        answer = SimpleNamespace(question=question)
        user_exam = SimpleNamespace(
            id=41,
            submitted_at=None,
            question_order=[7],
            current_index=0,
            answers=SimpleNamespace(get=lambda **kwargs: answer),
            time_remaining=lambda: 300,
            save=lambda: None,
        )

        rendered_orders = []

        def capture_render(request, template, context):
            rendered_orders.append([choice.id for choice in context["choices"]])
            return None

        # A regression to random.shuffle would make this test fail immediately.
        with patch("quiz.views.exams.get_object_or_404", return_value=user_exam), patch(
            "quiz.views.exams.render", side_effect=capture_render
        ), patch(
            "quiz.views.exams.random.shuffle",
            side_effect=AssertionError("global random.shuffle must not be used"),
        ):
            exam_question.__wrapped__(request, 41, 0)
            exam_question.__wrapped__(request, 41, 0)

        self.assertEqual(len(rendered_orders), 2)
        self.assertEqual(rendered_orders[0], rendered_orders[1])
        self.assertCountEqual(rendered_orders[0], [1, 2, 3, 4, 5])
