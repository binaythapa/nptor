# quiz/api_views.py
import math
import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import Exam, Question, Choice, UserExam, UserAnswer, ExamCategoryAllocation
from .serializers import ExamSerializer

# Reuse allocation function (same logic as in views.py)
def allocate_questions_for_exam(exam):
    total_needed = int(exam.question_count)
    allocations = list(exam.allocations.select_related('category').all())

    if not allocations:
        qs = Question.objects.filter(category=exam.category) if exam.category else Question.objects.all()
        return list(qs.order_by('?')[:total_needed])

    selected_qs = []
    remaining_needed = total_needed
    percent_allocs = []
    percent_sum = 0

    for a in allocations:
        if a.fixed_count:
            cat = a.category
            try:
                cat_ids = cat.get_descendants_include_self()
            except Exception:
                cat_ids = [cat.id]
            pool = list(Question.objects.filter(category_id__in=cat_ids))
            random.shuffle(pool)
            take = min(len(pool), a.fixed_count)
            selected_qs.extend(pool[:take])
            remaining_needed -= take
        else:
            percent_allocs.append(a)
            percent_sum += a.percentage

    percent_counts = {}
    if percent_allocs and remaining_needed > 0 and percent_sum > 0:
        raw = []
        for a in percent_allocs:
            scaled_fraction = (a.percentage / percent_sum) * remaining_needed
            count_floor = math.floor(scaled_fraction)
            remainder = scaled_fraction - count_floor
            raw.append((a, count_floor, remainder))
        for a, cnt, rem in raw:
            percent_counts[a.id] = cnt
        allocated = sum(percent_counts.values())
        left = remaining_needed - allocated
        raw_sorted = sorted(raw, key=lambda x: x[2], reverse=True)
        i = 0
        while left > 0 and i < len(raw_sorted):
            a, cnt, rem = raw_sorted[i]
            percent_counts[a.id] += 1
            left -= 1
            i += 1

        already_selected_ids = {q.id for q in selected_qs}
        for a in percent_allocs:
            cnt = percent_counts.get(a.id, 0)
            if cnt <= 0:
                continue
            try:
                cat_ids = a.category.get_descendants_include_self()
            except Exception:
                cat_ids = [a.category.id]
            pool = list(Question.objects.filter(category_id__in=cat_ids).exclude(id__in=already_selected_ids))
            random.shuffle(pool)
            take = min(len(pool), cnt)
            chosen = pool[:take]
            selected_qs.extend(chosen)
            already_selected_ids.update({q.id for q in chosen})

    if len(selected_qs) < total_needed:
        needed = total_needed - len(selected_qs)
        if exam.category:
            try:
                cat_ids = exam.category.get_descendants_include_self()
            except Exception:
                cat_ids = [exam.category.id]
            pool = list(Question.objects.filter(category_id__in=cat_ids).exclude(id__in={q.id for q in selected_qs}))
            random.shuffle(pool)
            take = min(len(pool), needed)
            selected_qs.extend(pool[:take])

    if len(selected_qs) < total_needed:
        needed = total_needed - len(selected_qs)
        pool = list(Question.objects.exclude(id__in={q.id for q in selected_qs}))
        random.shuffle(pool)
        take = min(len(pool), needed)
        selected_qs.extend(pool[:take])

    if len(selected_qs) > total_needed:
        random.shuffle(selected_qs)
        selected_qs = selected_qs[:total_needed]
    else:
        random.shuffle(selected_qs)

    return selected_qs

# -------------------------
# API Views
# -------------------------
class ExamListAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        exams = Exam.objects.filter(is_published=True)
        serializer = ExamSerializer(exams, many=True)
        return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_exam(request, pk):
    exam = get_object_or_404(Exam, pk=pk, is_published=True)
    existing = UserExam.objects.filter(user=request.user, exam=exam, submitted_at__isnull=True).first()
    if existing:
        ue = existing
    else:
        ue = UserExam.objects.create(user=request.user, exam=exam)
        qs = allocate_questions_for_exam(exam)
        ue.question_order = [q.id for q in qs]
        ue.save()
        for q in qs:
            UserAnswer.objects.create(user_exam=ue, question=q)

    payload = []
    for ua in ue.answers.select_related('question').all():
        q = ua.question
        choices = [{'id': c.id, 'text': c.text} for c in q.choices.all()] if q.question_type in ('single','multi','tf','dropdown') else []
        payload.append({
            'question_id': q.id,
            'text': q.text,
            'question_type': q.question_type,
            'difficulty': q.difficulty,
            'allow_multiple': q.question_type == 'multi',
            'choices': choices,
            'matching_pairs': q.matching_pairs,
            'ordering_items': q.ordering_items,
            'numeric_tolerance': q.numeric_tolerance,
        })

    return Response({'attempt_id': ue.id, 'duration_seconds': ue.exam.duration_seconds, 'questions': payload})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def attempt_detail(request, attempt_id):
    ue = get_object_or_404(UserExam, pk=attempt_id, user=request.user)
    data = []
    for ua in ue.answers.select_related('question','choice'):
        data.append({
            'question_id': ua.question.id,
            'question': ua.question.text,
            'selected_choice': ua.choice.id if ua.choice else None,
            'selections': ua.selections,
            'raw_answer': ua.raw_answer
        })
    return Response({'attempt': ue.id, 'time_remaining': ue.time_remaining(), 'questions': data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_submit_attempt(request, attempt_id):
    ue = get_object_or_404(UserExam, pk=attempt_id, user=request.user)
    if not ue.is_active():
        return Response({'detail': 'Attempt closed'}, status=400)

    answers = request.data.get('answers', {})
    total = 0
    score_acc = 0.0

    for ua in ue.answers.select_related('question'):
        q = ua.question
        total += 1

        if q.question_type in ('single','dropdown','tf'):
            choice_id = answers.get(str(q.id))
            if choice_id:
                try:
                    ch = Choice.objects.get(pk=int(choice_id), question=q)
                    ua.choice = ch
                    ua.is_correct = ch.is_correct
                    if ua.is_correct:
                        score_acc += 1.0
                except Exception:
                    ua.choice = None
                    ua.is_correct = False
            else:
                ua.choice = None
                ua.is_correct = False
            ua.selections = None
            ua.raw_answer = None
            ua.save()

        elif q.question_type == 'multi':
            sel = answers.get(str(q.id), [])
            sel_ids = [int(x) for x in sel if x]
            ua.selections = sel_ids
            correct_ids = [c.id for c in q.choices.filter(is_correct=True)]
            if not correct_ids:
                frac = 0.0
            else:
                tp = len(set(sel_ids) & set(correct_ids))
                fp = len(set(sel_ids) - set(correct_ids))
                frac = max(0.0, (tp - 0.5 * fp) / len(correct_ids))
            score_acc += frac
            ua.choice = None
            ua.is_correct = None
            ua.raw_answer = None
            ua.save()

        elif q.question_type == 'fill':
            raw = (answers.get(str(q.id)) or '').strip()
            ua.raw_answer = raw
            def norm(s): return ' '.join(s.lower().split())
            if q.correct_text:
                ua.is_correct = norm(raw) == norm(q.correct_text)
                if ua.is_correct:
                    score_acc += 1.0
            else:
                ua.is_correct = False
            ua.selections = None
            ua.choice = None
            ua.save()

        elif q.question_type == 'numeric':
            raw = (answers.get(str(q.id)) or '').strip()
            ua.raw_answer = raw
            try:
                v = float(raw)
                if q.numeric_answer is not None:
                    tol = q.numeric_tolerance or 0.0
                    if abs(v - float(q.numeric_answer)) <= float(tol):
                        ua.is_correct = True
                        score_acc += 1.0
                    else:
                        ua.is_correct = False
                else:
                    ua.is_correct = False
            except Exception:
                ua.is_correct = False
            ua.selections = None
            ua.choice = None
            ua.save()

        elif q.question_type == 'match':
            pairs = q.matching_pairs or []
            tp = 0
            fp = 0
            for i, pair in enumerate(pairs):
                sel = answers.get(f'{q.id}_{i}')
                if sel and str(sel) == str(pair.get('right')):
                    tp += 1
                else:
                    fp += 1
            denom = len(pairs) if pairs else 1
            frac = max(0.0, (tp - 0.5 * fp) / denom)
            score_acc += frac
            ua.selections = None
            ua.choice = None
            ua.raw_answer = None
            ua.save()

        elif q.question_type == 'order':
            raw = (answers.get(str(q.id)) or '').strip()
            ua.raw_answer = raw
            try:
                user_order = [x.strip() for x in raw.split(',') if x.strip()]
                canonical = q.ordering_items or []
                correct_pos = 0
                denom = max(1, len(canonical))
                for i, val in enumerate(user_order):
                    if i < len(canonical) and canonical[i].strip().lower() == val.strip().lower():
                        correct_pos += 1
                frac = correct_pos / denom
                score_acc += frac
            except Exception:
                pass
            ua.selections = None
            ua.choice = None
            ua.save()

        else:
            ua.choice = None
            ua.is_correct = False
            ua.selections = None
            ua.raw_answer = None
            ua.save()

    ue.score = (score_acc / total) * 100 if total else 0
    ue.submitted_at = timezone.now()
    ue.save()
    return Response({'score': ue.score})
