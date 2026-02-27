import random
import time


def select_adaptive_question(plan, questions_queryset, request=None):
    """
    Advanced Lightweight Adaptive Engine
    - Weak category boosting
    - Difficulty targeting
    - Streak escalation
    - Mistake reinforcement
    - Spaced repetition decay
    - Exam-mode simulation
    """

    questions = list(questions_queryset)

    if not questions:
        return None

    category_stats = plan.category_stats or {}
    difficulty_stats = plan.difficulty_stats or {}

    mastery = plan.accuracy_percentage()
    streak = plan.current_streak

    # Session-based adaptive signals
    mistakes = request.session.get("recent_mistakes", {}) if request else {}
    history = request.session.get("question_history", {}) if request else {}
    exam_mode = request.session.get("exam_mode", False) if request else False

    weighted_pool = []

    now = time.time()

    for q in questions:

        # ==========================================================
        # 1️⃣ CATEGORY WEAKNESS WEIGHT
        # ==========================================================
        cat_key = str(q.category_id)
        cat_data = category_stats.get(cat_key, {})

        attempted = cat_data.get("attempted", 0)
        correct = cat_data.get("correct", 0)

        if attempted > 0:
            cat_accuracy = correct / attempted
        else:
            cat_accuracy = 0.5  # neutral baseline

        category_weight = 1 + (1 - cat_accuracy) * 2


        # ==========================================================
        # 2️⃣ DIFFICULTY TARGETING
        # ==========================================================
        difficulty_weight = 1

        if mastery < 60:
            if q.difficulty == "easy":
                difficulty_weight = 1.6
            elif q.difficulty == "medium":
                difficulty_weight = 1.2
            else:
                difficulty_weight = 0.7

        elif mastery < 80:
            if q.difficulty == "medium":
                difficulty_weight = 1.5
            elif q.difficulty == "hard":
                difficulty_weight = 1.2

        else:
            if q.difficulty == "hard":
                difficulty_weight = 1.7
            elif q.difficulty == "medium":
                difficulty_weight = 1.3


        # ==========================================================
        # 3️⃣ STREAK ESCALATION
        # ==========================================================
        streak_bonus = 1 + min(streak / 20, 0.5)


        # ==========================================================
        # 4️⃣ MISTAKE REINFORCEMENT
        # ==========================================================
        mistake_weight = 1
        qid_str = str(q.id)

        if qid_str in mistakes:
            mistake_weight += mistakes[qid_str] * 0.5


        # ==========================================================
        # 5️⃣ SPACED REPETITION DECAY
        # ==========================================================
        spacing_weight = 1

        if qid_str in history:
            time_since = now - history[qid_str]

            # If seen recently (<5 min), reduce weight
            if time_since < 300:
                spacing_weight = 0.4
            elif time_since < 1800:
                spacing_weight = 0.7
            else:
                spacing_weight = 1.2  # revive older questions


        # ==========================================================
        # 6️⃣ EXAM MODE SIMULATION
        # ==========================================================
        exam_weight = 1

        if exam_mode:
            # In exam mode, reduce weakness bias
            category_weight = 1 + (1 - cat_accuracy)

            # Slightly favor harder questions
            if q.difficulty == "hard":
                exam_weight = 1.3


        # ==========================================================
        # 7️⃣ FINAL WEIGHT
        # ==========================================================
        final_weight = (
            category_weight *
            difficulty_weight *
            streak_bonus *
            mistake_weight *
            spacing_weight *
            exam_weight
        )

        # Add controlled randomness
        final_weight *= random.uniform(0.9, 1.1)

        weighted_pool.append((q, final_weight))


    # ==========================================================
    # Weighted Random Selection
    # ==========================================================
    total_weight = sum(w for _, w in weighted_pool)

    if total_weight == 0:
        return random.choice(questions)

    r = random.uniform(0, total_weight)
    upto = 0

    for q, w in weighted_pool:
        if upto + w >= r:
            return q
        upto += w

    return questions[0]