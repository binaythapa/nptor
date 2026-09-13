from django.test import TestCase

from quiz.models import Exam, ExamTrack
from quiz.track_forms import TrackExamFormSet


class TrackExamFormSetTests(TestCase):
    def _exam(self, title):
        return Exam.objects.create(
            title=title,
            duration_seconds=600,
            question_count=10,
            is_published=True,
        )

    def _data(self, rows):
        data = {
            "track_exams-TOTAL_FORMS": str(len(rows)),
            "track_exams-INITIAL_FORMS": "0",
            "track_exams-MIN_NUM_FORMS": "0",
            "track_exams-MAX_NUM_FORMS": "1000",
        }
        for index, row in enumerate(rows):
            data[f"track_exams-{index}-exam"] = str(row["exam"].pk)
            data[f"track_exams-{index}-order"] = str(row.get("order", index + 1))
            data[f"track_exams-{index}-is_required"] = "on"
            data[f"track_exams-{index}-prerequisite_exams"] = [
                str(item.pk) for item in row.get("prerequisites", [])
            ]
        return data

    def test_prerequisites_must_be_included_in_track(self):
        exam_a = self._exam("Alpha Exam")
        exam_b = self._exam("Beta Exam")
        formset = TrackExamFormSet(
            self._data([
                {"exam": exam_a, "prerequisites": [exam_b]},
            ]),
            instance=ExamTrack(),
        )

        self.assertFalse(formset.is_valid())
        self.assertIn(
            "Prerequisite exams must also be included in this Track.",
            formset.forms[0].errors["prerequisite_exams"].as_text(),
        )

    def test_self_prerequisite_is_rejected(self):
        exam_a = self._exam("Alpha Exam")
        formset = TrackExamFormSet(
            self._data([
                {"exam": exam_a, "prerequisites": [exam_a]},
            ]),
            instance=ExamTrack(),
        )

        self.assertFalse(formset.is_valid())
        self.assertIn(
            "An exam cannot be a prerequisite of itself.",
            formset.forms[0].errors["prerequisite_exams"].as_text(),
        )

    def test_included_prerequisite_is_valid(self):
        exam_a = self._exam("Alpha Exam")
        exam_b = self._exam("Beta Exam")
        formset = TrackExamFormSet(
            self._data([
                {"exam": exam_a},
                {"exam": exam_b, "prerequisites": [exam_a]},
            ]),
            instance=ExamTrack(),
        )

        self.assertTrue(formset.is_valid())
