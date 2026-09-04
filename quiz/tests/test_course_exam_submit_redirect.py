from django.test import SimpleTestCase


class CourseQuizSubmitRedirectTests(SimpleTestCase):
    def test_course_exam_context_redirect_target(self):
        from quiz.views.exams import get_course_exam_redirect_url

        self.assertEqual(
            get_course_exam_redirect_url(
                {"course_slug": "demo-aws-cloud-course", "lesson_id": 8}
            ),
            "/courses/demo-aws-cloud-course/learn/8/",
        )

    def test_standalone_exam_has_no_course_redirect(self):
        from quiz.views.exams import get_course_exam_redirect_url

        self.assertIsNone(get_course_exam_redirect_url({}))
