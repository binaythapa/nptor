# Standard library imports
import math
from datetime import timedelta

# Django imports
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, F, Count, Max, Sum

# App imports
from quiz.models import (
    StudyPlan,
    Question,
    Domain,
    Category,
)
from quiz.services.study_plan_service import generate_study_plan
from quiz.services.adaptive_engine import select_adaptive_question
from quiz.utils import calculate_global_percentile


from django.contrib.auth.decorators import login_required
from django.shortcuts import render



@login_required
def study_plan_dashboard(request):

    active_plan = request.user.study_plans.filter(
        is_active=True,
        is_completed=False
    ).first()

    history_plans = request.user.study_plans.filter(
        is_active=False
    ).order_by("-created_at")[:5]

    analytics = None
    category_analytics = []
    weak_categories = []
    suggestion = None
    trend_percent = None
    sparkline_data = []

    if active_plan:

        active_plan.auto_extend_if_needed()

        # ================= BASIC STATS =================
        total_done = sum(active_plan.daily_progress.values())
        total_questions = active_plan.total_questions()

        total_attempted = active_plan.total_attempted
        total_correct = active_plan.total_correct

        accuracy_percent = (
            round((total_correct / total_attempted) * 100, 2)
            if total_attempted > 0 else 0
        )

        # ================= CATEGORY ANALYTICS =================
        stats = active_plan.category_stats or {}
        category_ids = list(stats.keys())

        categories = {
            c.id: c
            for c in Category.objects.filter(id__in=category_ids)
        }

        for cat_id, data in stats.items():
            attempted = data.get("attempted", 0)
            correct = data.get("correct", 0)

            if attempted == 0:
                continue

            percent = round((correct / attempted) * 100, 2)
            category_obj = categories.get(int(cat_id))

            category_data = {
                "id": cat_id,
                "name": category_obj.name if category_obj else f"Category {cat_id}",
                "attempted": attempted,
                "correct": correct,
                "accuracy": percent,
            }

            category_analytics.append(category_data)

            if percent < 60 and attempted >= 5:
                weak_categories.append(category_data)

        # ================= TREND =================
        if history_plans.exists():
            previous_plan = history_plans.first()

            if previous_plan.total_attempted > 0:
                previous_accuracy = (
                    previous_plan.total_correct /
                    previous_plan.total_attempted
                ) * 100

                trend_percent = round(
                    accuracy_percent - previous_accuracy,
                    2
                )

        # ================= SPARKLINE =================
        for plan in reversed(history_plans):
            if plan.total_attempted > 0:
                sparkline_data.append(
                    round(
                        (plan.total_correct / plan.total_attempted) * 100,
                        2
                    )
                )

        if total_attempted > 0:
            sparkline_data.append(accuracy_percent)

        # ================= SUGGESTION =================
        if weak_categories:
            suggestion = "Create a 5-day focused mini-plan for weak topics."
        elif accuracy_percent >= 80:
            suggestion = "Upgrade to 30-day advanced mastery plan."
        elif accuracy_percent >= 60:
            suggestion = "Continue with structured 15-day improvement plan."
        else:
            suggestion = "Repeat 7-day revision plan."

        # ================= MASTERY SCORE =================
        volume_score = min(100, (total_attempted / 200) * 100)

        days_practiced = len([
            v for v in active_plan.daily_progress.values()
            if v > 0
        ])

        total_days = active_plan.total_plan_days()

        consistency_ratio = (
            days_practiced / total_days
            if total_days > 0 else 0
        )

        consistency_score = consistency_ratio * 100
        weak_penalty = min(len(weak_categories) * 5, 20)

        mastery_score = (
            (accuracy_percent * 0.6) +
            (volume_score * 0.25) +
            (consistency_score * 0.15)
        ) - weak_penalty

        mastery_score = round(max(mastery_score, 0), 2)

        # ================= ADVANCED METRICS =================
        difficulty_mastery = active_plan.difficulty_weighted_mastery()
        readiness_score = active_plan.certification_readiness()
        badge = active_plan.certification_badge()

        prediction = active_plan.certification_prediction()
        volatility = active_plan.score_volatility()

        if volatility < 0.15:
            confidence_band = "High"
        elif volatility < 0.30:
            confidence_band = "Medium"
        else:
            confidence_band = "Low"

        # ================= FINAL ANALYTICS DICT =================
        analytics = {
            "completion_percent": active_plan.completion_percentage(),
            "total_done": total_done,
            "total_questions": total_questions,
            "accuracy_percent": accuracy_percent,
            "trend_percent": trend_percent,
            "sparkline_data": sparkline_data,
            "days_remaining": max(
                0,
                active_plan.total_plan_days() - active_plan.get_day_index()
            ),
            "extension_used": active_plan.extension_days,
            "mastery_score": mastery_score,

            # Gamification
            "level_progress": active_plan.level_progress_percent(),
            "badge": badge,
            "global_percentile": calculate_global_percentile(active_plan),

            # Readiness
            "difficulty_mastery": difficulty_mastery,
            "readiness_score": readiness_score,

            # Prediction
            "predicted_score": prediction["predicted_score"],
            "pass_probability": prediction["pass_probability"],
            "confidence_level": prediction["confidence"],

            # Stability
            "volatility": volatility,
            "confidence_band": confidence_band,

            # Exam Mode
            "exam_mode": getattr(active_plan, "exam_mode", False),
        }

    context = {
        "active_plan": active_plan,
        "analytics": analytics,
        "category_analytics": category_analytics,
        "weak_categories": weak_categories,
        "suggestion": suggestion,
        "history_plans": history_plans,
    }

    return render(
        request,
        "quiz/study_plan/dashboard.html",
        context
    )













@login_required
def clone_study_plan(request, plan_id):

    old_plan = request.user.study_plans.filter(id=plan_id).first()

    if not old_plan:
        return redirect("quiz:study_plan_dashboard")

    from quiz.services.study_plan_service import generate_study_plan

    new_plan = generate_study_plan(
        user=request.user,
        plan_type=old_plan.plan_type,
        domain=old_plan.domain
    )

    return redirect("quiz:study_plan_dashboard")
    

from django.utils import timezone
from datetime import timedelta
from time import time
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from django.utils import timezone
from datetime import timedelta
from time import time
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


@login_required
def study_plan_practice(request):

    # ================= ACTIVE PLAN =================
    plan = request.user.study_plans.filter(
        is_active=True,
        is_completed=False
    ).first()

    if not plan:
        return redirect("quiz:study_plan_dashboard")

    # ================= DAILY SESSION RESET =================
    today_key = f"plan_day_{plan.get_day_index()}"
    last_day = request.session.get("plan_day_key")

    if last_day != today_key:
        request.session["plan_day_key"] = today_key
        request.session["sp_seen"] = []
        request.session.pop("sp_qid", None)

    seen = request.session.get("sp_seen", [])

    # ================= PLAN EXPIRED =================
    if plan.get_day_index() >= plan.total_plan_days():
        return render(
            request,
            "quiz/study_plan/plan_expired.html",
            {"plan": plan}
        )

    # ================= DAILY LIMIT =================
    if plan.get_today_completed_count() >= plan.questions_per_day:
        return redirect("quiz:study_plan_dashboard")

    # ================= TODAY QUESTIONS =================
    today_ids = plan.get_today_question_ids()

    qs = (
        Question.objects
        .filter(
            id__in=today_ids,
            question_type__in=[
                Question.SINGLE,
                Question.MULTI,
                Question.TRUE_FALSE,
            ],
            is_active=True,
            is_deleted=False,
        )
        .prefetch_related("choices")
    )

    remaining = qs.exclude(id__in=seen)

    if not remaining.exists():
        return redirect("quiz:study_plan_dashboard")

    # ================= PICK QUESTION (ADAPTIVE SAFE) =================
    qid = request.session.get("sp_qid")
    question = remaining.filter(id=qid).first() if qid else None

    if not question:
        question = select_adaptive_question(plan, remaining, request) or remaining.first()
        request.session["sp_qid"] = question.id

    choices = question.choices.order_by("order", "id")

    # ============================================================
    # ================= HANDLE SUBMIT ============================
    # ============================================================

    if request.method == "POST":

        # ---------- Evaluate ----------
        is_correct = False

        if question.question_type == Question.MULTI:
            selected_ids = list(map(int, request.POST.getlist("choice_multi")))
            correct_ids = list(
                question.choices
                .filter(is_correct=True)
                .values_list("id", flat=True)
            )
            is_correct = set(selected_ids) == set(correct_ids)

        else:
            selected_id = request.POST.get("choice")
            selected = question.choices.filter(id=selected_id).first()
            is_correct = selected and selected.is_correct

        # ============================================================
        # ================= AGGREGATE STATS ==========================
        # ============================================================

        plan.total_attempted += 1
        if is_correct:
            plan.total_correct += 1

        # ---------- Category Stats ----------
        cat_key = str(question.category_id)
        category_stats = plan.category_stats or {}

        if cat_key not in category_stats:
            category_stats[cat_key] = {"attempted": 0, "correct": 0}

        category_stats[cat_key]["attempted"] += 1
        if is_correct:
            category_stats[cat_key]["correct"] += 1

        plan.category_stats = category_stats

        # ---------- Difficulty Stats ----------
        diff_key = question.difficulty
        difficulty_stats = plan.difficulty_stats or {}

        if diff_key not in difficulty_stats:
            difficulty_stats[diff_key] = {"attempted": 0, "correct": 0}

        difficulty_stats[diff_key]["attempted"] += 1
        if is_correct:
            difficulty_stats[diff_key]["correct"] += 1

        plan.difficulty_stats = difficulty_stats

        # ============================================================
        # ================= PERFORMANCE HISTORY ======================
        # ============================================================

        history = plan.performance_history or []
        history.append(1 if is_correct else 0)
        plan.performance_history = history[-50:]  # keep last 50

        # ============================================================
        # ================= MISTAKE REINFORCEMENT ====================
        # ============================================================

        mistakes = request.session.get("recent_mistakes", {})
        qid_str = str(question.id)

        if not is_correct:
            mistakes[qid_str] = mistakes.get(qid_str, 0) + 3
        else:
            if qid_str in mistakes:
                mistakes[qid_str] = max(mistakes[qid_str] - 2, 0)

        request.session["recent_mistakes"] = mistakes

        # ============================================================
        # ================= SPACED REPETITION ========================
        # ============================================================

        history_map = request.session.get("question_history", {})
        history_map[qid_str] = time()
        request.session["question_history"] = history_map

        # ============================================================
        # ================= STREAK SYSTEM ============================
        # ============================================================

        today = timezone.now().date()

        if plan.last_activity_date == today:
            pass
        elif plan.last_activity_date == today - timedelta(days=1):
            plan.current_streak += 1
        else:
            plan.current_streak = 1

        plan.last_activity_date = today

        if plan.current_streak > plan.longest_streak:
            plan.longest_streak = plan.current_streak

        # ============================================================
        # ================= XP SYSTEM ================================
        # ============================================================

        base_xp = 2

        if is_correct:
            base_xp += 10

        difficulty_bonus = {
            "easy": 0,
            "medium": 3,
            "hard": 5,
        }

        base_xp += difficulty_bonus.get(question.difficulty, 0)

        streak_bonus = min(plan.current_streak, 10)
        base_xp += streak_bonus

        leveled_up = plan.apply_xp(base_xp)

        request.session["xp_gain"] = base_xp

        if leveled_up:
            request.session["level_up"] = {
                "new_level": plan.level
            }

        # ============================================================
        # ================= AUTO EXAM MODE ===========================
        # ============================================================

        if plan.certification_readiness() < 65 and \
           plan.get_day_index() >= plan.total_days - 7:
            plan.exam_mode = True

        # ============================================================
        # ================= SINGLE SAVE ==============================
        # ============================================================

        plan.save(update_fields=[
            "total_attempted",
            "total_correct",
            "category_stats",
            "difficulty_stats",
            "performance_history",
            "current_streak",
            "longest_streak",
            "last_activity_date",
            "xp",
            "level",
            "exam_mode",
        ])

        # ============================================================
        # ================= MARK COMPLETED ===========================
        # ============================================================

        seen.append(question.id)
        request.session["sp_seen"] = seen
        request.session.pop("sp_qid", None)

        plan.increment_today_progress()
        plan.mark_completed_if_finished()

        return redirect("quiz:study_plan_practice")

    # ============================================================
    # ================= RENDER ==============================
    # ============================================================

    return render(
        request,
        "quiz/study_plan/practice.html",
        {
            "question": question,
            "choices": choices,
            "daily_target": plan.questions_per_day,
            "today_completed": plan.get_today_completed_count(),
            "level_up_data": request.session.pop("level_up", None),
            "xp_gain": request.session.pop("xp_gain", None),
        }
    )



@login_required
def create_study_plan(request):

    if request.method == "POST":
        plan_type = int(request.POST.get("plan_type"))
        domain_id = request.POST.get("domain")

        domain = None
        if domain_id:
            domain = Domain.objects.filter(id=domain_id, is_active=True).first()

        try:
            generate_study_plan(
                user=request.user,
                plan_type=plan_type,
                domain=domain
            )
            messages.success(request, "Study Plan created successfully!")
            return redirect("quiz:study_plan_dashboard")

        except Exception as e:
            messages.error(request, str(e))

    domains = Domain.objects.filter(is_active=True)

    return render(request, "quiz/study_plan/create_plan.html", {
        "domains": domains
    })




@login_required
def create_adaptive_plan(request):
    """
    Auto-generate next plan based on user's readiness score
    """

    # Get latest completed plan
    last_plan = request.user.study_plans.filter(
        is_completed=True
    ).order_by("-created_at").first()

    if not last_plan:
        messages.warning(request, "Complete a study plan first.")
        return redirect("quiz:study_plan_dashboard")

    readiness = last_plan.certification_readiness()

    # Decide plan type
    if readiness >= 85:
        plan_type = StudyPlan.PLAN_30
        days = 30
        per_day = 25
    elif readiness >= 65:
        plan_type = StudyPlan.PLAN_15
        days = 15
        per_day = 40
    else:
        plan_type = StudyPlan.PLAN_7
        days = 7
        per_day = 60

    # Select questions
    total_needed = days * per_day

    questions = Question.objects.filter(
        is_active=True,
        is_deleted=False
    ).values_list("id", flat=True)[:total_needed]

    # Deactivate current active plans
    request.user.study_plans.filter(
        is_active=True
    ).update(is_active=False)

    StudyPlan.objects.create(
        user=request.user,
        plan_type=plan_type,
        total_days=days,
        questions_per_day=per_day,
        question_ids=list(questions),
        start_date=timezone.now().date(),
    )

    messages.success(request, "Adaptive study plan created successfully!")

    return redirect("quiz:study_plan_dashboard")


@login_required
def study_plan_leaderboard(request):

    domain_id = request.GET.get("domain")
    month_filter = request.GET.get("monthly")

    plans = StudyPlan.objects.filter(is_completed=True).select_related("user")

    # ================= DOMAIN FILTER =================
    if domain_id:
        plans = plans.filter(domain_id=domain_id)

    # ================= MONTHLY RESET =================
    if month_filter == "1":
        now = timezone.now()
        plans = plans.filter(
            created_at__year=now.year,
            created_at__month=now.month
        )

    # ================= BEST PLAN PER USER =================
    # Prevent duplicate users appearing multiple times
    best_plans = {}

    for plan in plans:
        readiness = plan.certification_readiness()

        if (
            plan.user_id not in best_plans
            or readiness > best_plans[plan.user_id]["readiness"]
        ):
            best_plans[plan.user_id] = {
                "plan": plan,
                "readiness": readiness
            }

    ranked = sorted(
        best_plans.values(),
        key=lambda x: x["readiness"],
        reverse=True
    )

    total_users = len(ranked)

    leaderboard = []

    for index, item in enumerate(ranked, start=1):

        plan = item["plan"]
        readiness = item["readiness"]

        percentile = (
            round((total_users - index) / total_users * 100, 2)
            if total_users > 0 else 0
        )

        leaderboard.append({
            "rank": index,
            "user": plan.user,
            "mastery": readiness,
            "xp": getattr(plan, "xp", plan.total_correct * 10),
            "streak": plan.longest_streak,
            "percentile": percentile,
        })

    return render(
        request,
        "quiz/study_plan/leaderboard.html",
        {
            "leaderboard": leaderboard,
            "domains": Domain.objects.filter(is_active=True),
        }
    )