# quiz/services/streak_service.py

import datetime
import zoneinfo
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from quiz.models.practice import UserPracticeStreak, DailyPracticeLog

KATHMANDU_TZ = zoneinfo.ZoneInfo("Asia/Kathmandu")


def get_business_today():
    """
    Returns today's date in the Asia/Kathmandu business timezone.
    Consistent business timezone policy across all streak calculations.
    """
    return timezone.now().astimezone(KATHMANDU_TZ).date()


def record_qualifying_practice(user, question=None, is_correct=False, source="practice"):
    """
    Records a qualifying daily practice activity for an authenticated student.
    
    Guarantees:
    1. Maximum of one active day counted per calendar day (Asia/Kathmandu).
    2. Atomic streak updates using database row locking (select_for_update).
    3. Safe handling of duplicate submissions on the same day.
    4. Accurate consecutive-day increment and missed-day reset.
    """
    if not user or not user.is_authenticated:
        return None, None

    today = get_business_today()

    with transaction.atomic():
        # 1. Atomic log record (Unique constraint prevents duplicates)
        log, created = DailyPracticeLog.objects.select_for_update().get_or_create(
            user=user,
            activity_date=today,
            defaults={
                "questions_practiced": 1,
                "questions_correct": 1 if is_correct else 0,
                "is_qualifying": True,
            },
        )
        if not created:
            log.questions_practiced += 1
            if is_correct:
                log.questions_correct += 1
            log.save(update_fields=["questions_practiced", "questions_correct", "updated_at"])

        # 2. Atomic streak calculation
        streak_obj, _ = UserPracticeStreak.objects.select_for_update().get_or_create(
            user=user,
            defaults={
                "current_streak": 0,
                "longest_streak": 0,
                "total_active_days": 0,
            },
        )

        streak_obj.total_questions_practiced += 1
        if is_correct:
            streak_obj.total_questions_correct += 1

        last_date = streak_obj.last_activity_date

        if last_date == today:
            # Already active today: keep current streak unchanged
            streak_obj.save(update_fields=[
                "total_questions_practiced",
                "total_questions_correct",
                "updated_at",
            ])
        elif last_date == today - datetime.timedelta(days=1):
            # Consecutive day: increment streak
            streak_obj.current_streak += 1
            if streak_obj.current_streak > streak_obj.longest_streak:
                streak_obj.longest_streak = streak_obj.current_streak
            streak_obj.last_activity_date = today
            streak_obj.total_active_days += 1
            streak_obj.save(update_fields=[
                "current_streak",
                "longest_streak",
                "last_activity_date",
                "total_active_days",
                "total_questions_practiced",
                "total_questions_correct",
                "updated_at",
            ])
        else:
            # Missed one or more days (or first day ever): streak resets to 1
            streak_obj.current_streak = 1
            if streak_obj.current_streak > streak_obj.longest_streak:
                streak_obj.longest_streak = streak_obj.current_streak
            streak_obj.last_activity_date = today
            streak_obj.total_active_days += 1
            streak_obj.save(update_fields=[
                "current_streak",
                "longest_streak",
                "last_activity_date",
                "total_active_days",
                "total_questions_practiced",
                "total_questions_correct",
                "updated_at",
            ])

    return streak_obj, log


def get_student_streak_summary(user, today=None):
    """
    Returns the comprehensive streak and weekly activity summary for a student.
    """
    if not user or not user.is_authenticated:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "last_activity_date": None,
            "is_active_today": False,
            "total_active_days": 0,
            "total_questions_practiced": 0,
            "total_questions_correct": 0,
            "accuracy_percent": 0.0,
            "weekly_summary": [],
        }

    if today is None:
        today = get_business_today()

    streak_obj = UserPracticeStreak.objects.filter(user=user).first()
    if not streak_obj:
        current_streak = 0
        longest_streak = 0
        last_date = None
        total_active_days = 0
        total_practiced = 0
        total_correct = 0
    else:
        current_streak = streak_obj.get_effective_current_streak(today=today)
        longest_streak = streak_obj.longest_streak
        last_date = streak_obj.last_activity_date
        total_active_days = streak_obj.total_active_days
        total_practiced = streak_obj.total_questions_practiced
        total_correct = streak_obj.total_questions_correct

    is_active_today = (last_date == today)
    accuracy = (
        round((total_correct / total_practiced) * 100, 1)
        if total_practiced > 0 else 0.0
    )

    # Weekly activity summary (last 7 days ending today)
    start_date = today - datetime.timedelta(days=6)
    logs = {
        log.activity_date: log
        for log in DailyPracticeLog.objects.filter(
            user=user,
            activity_date__gte=start_date,
            activity_date__lte=today,
        )
    }

    weekly_summary = []
    for i in range(7):
        d = start_date + datetime.timedelta(days=i)
        log_entry = logs.get(d)
        weekly_summary.append({
            "date": d,
            "day_name": d.strftime("%a"),
            "is_today": (d == today),
            "is_active": (log_entry is not None and log_entry.questions_practiced > 0),
            "questions_count": log_entry.questions_practiced if log_entry else 0,
            "correct_count": log_entry.questions_correct if log_entry else 0,
        })

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "last_activity_date": last_date,
        "is_active_today": is_active_today,
        "total_active_days": total_active_days,
        "total_questions_practiced": total_practiced,
        "total_questions_correct": total_correct,
        "accuracy_percent": accuracy,
        "weekly_summary": weekly_summary,
    }
