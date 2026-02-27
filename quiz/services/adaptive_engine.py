import random
import time


def select_adaptive_question(plan, questions_queryset, request=None):
    """
    Advanced Adaptive Engine (Production Safe)

    Features:
    - Weak category prioritization
    - Difficulty targeting based on mastery
    - Streak escalation
    - Mistake reinforcement
    - Spaced repetition decay
    - Exam mode simulation
    - Volatility stabilization
    """

    questions = list(questions_queryset)

    if not questions:
        return None

    category_stats = plan.category_stats or {}
    difficulty_stats = plan.difficulty_stats or {}

    mastery = plan.accuracy_percentage()
    streak = plan.current_streak or 0

    # Session-based adaptive signals
    mistakes = request.session.get("recent_mistakes", {}) if request else {}
    history = request.session.get("question_history", {}) if request else {}
    exam_mode = getattr(plan, "exam_mode", False)

    # Optional volatility stabilizer
    volatility = getattr(plan, "score_volatility", lambda: 0.1)()
    volatility_factor = 1 + min(volatility, 0.3)

    weighted_pool = []
    now = time.time()

    for q in questions:

        qid_str = str(q.id)

        # ==========================================================
        # 1️⃣ CATEGORY WEIGHT
        # ==========================================================
        cat_key = str(q.category_id)
        cat_data = category_stats.get(cat_key, {})

        attempted = cat_data.get("attempted", 0)
        correct = cat_data.get("correct", 0)

        if attempted > 0:
            cat_accuracy = correct / attempted
        else:
            cat_accuracy = 0.5  # neutral

        # Weak categories boosted
        category_weight = 1 + (1 - cat_accuracy) * 1.8


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
                difficulty_weight = 1.6
            elif q.difficulty == "medium":
                difficulty_weight = 1.3


        # ==========================================================
        # 3️⃣ STREAK ESCALATION
        # ==========================================================
        streak_bonus = 1 + min(streak / 25, 0.4)


        # ==========================================================
        # 4️⃣ MISTAKE REINFORCEMENT
        # ==========================================================
        mistake_weight = 1

        if qid_str in mistakes:
            mistake_weight += min(mistakes[qid_str] * 0.4, 2.0)


        # ==========================================================
        # 5️⃣ SPACED REPETITION DECAY
        # ==========================================================
        spacing_weight = 1

        if qid_str in history:
            time_since = now - history[qid_str]

            if time_since < 300:
                spacing_weight = 0.4
            elif time_since < 1800:
                spacing_weight = 0.7
            elif time_since > 86400:
                spacing_weight = 1.3
            else:
                spacing_weight = 1


        # ==========================================================
        # 6️⃣ EXAM MODE SIMULATION
        # ==========================================================
        exam_weight = 1

        if exam_mode:
            # Reduce reinforcement bias
            category_weight = 1 + (1 - cat_accuracy)

            # Favor realistic exam difficulty
            if q.difficulty == "hard":
                exam_weight = 1.3
            elif q.difficulty == "medium":
                exam_weight = 1.2


        # ==========================================================
        # 7️⃣ FINAL WEIGHT
        # ==========================================================
        final_weight = (
            category_weight *
            difficulty_weight *
            streak_bonus *
            mistake_weight *
            spacing_weight *
            exam_weight *
            volatility_factor
        )

        # Prevent extreme explosion
        final_weight = max(final_weight, 0.05)

        # Controlled randomness
        final_weight *= random.uniform(0.92, 1.08)

        weighted_pool.append((q, final_weight))

    # ==========================================================
    # WEIGHTED RANDOM SELECTION
    # ==========================================================
    total_weight = sum(w for _, w in weighted_pool)

    if total_weight <= 0:
        return random.choice(questions)

    r = random.uniform(0, total_weight)
    upto = 0

    for q, w in weighted_pool:
        upto += w
        if upto >= r:
            return q

    return questions[0]