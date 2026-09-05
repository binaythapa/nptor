from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from quiz.models import Exam, ExamTrack, TrackExam


class IndependentExamTrackContractTests(SimpleTestCase):
    def test_exam_is_independent_of_track_and_pricing(self):
        field_names = {field.name for field in Exam._meta.get_fields()}

        self.assertNotIn("track", field_names)
        self.assertNotIn("prerequisite_exams", field_names)
        self.assertNotIn("is_free", field_names)
        self.assertNotIn("price", field_names)
        self.assertNotIn("currency", field_names)

    def test_track_exam_is_the_composition_boundary(self):
        field_names = {field.name for field in TrackExam._meta.get_fields()}

        self.assertIn("track", field_names)
        self.assertIn("exam", field_names)
        self.assertIn("position", field_names)
        self.assertIn("prerequisites", field_names)

    def test_track_exam_rejects_prerequisite_from_another_track(self):
        track_field = TrackExam._meta.get_field("track")
        self.assertEqual(track_field.remote_field.model, ExamTrack)

        prerequisite_field = TrackExam._meta.get_field("prerequisites")
        self.assertEqual(prerequisite_field.remote_field.model, TrackExam)

    def test_position_is_explicit_and_positive(self):
        field = TrackExam._meta.get_field("position")
        self.assertTrue(field.null is False)
        self.assertTrue(field.default == 1)
        self.assertTrue(field.validators)
