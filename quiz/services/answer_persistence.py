from django.db import transaction

from quiz.models import (
    UserExam,
    UserAnswer,
    Question,
    Choice,
)


def autosave_answers(
    ue: UserExam,
    post_data,
):
    """
    Persist partial answers safely.
    - Autosave-safe (does not erase existing answers)
    - Uses select_for_update to avoid race conditions
    - Supports all question types including match/order
    """

    # Build posted map: key -> list(values)
    posted = {}
    for k in post_data.keys():
        if k == "csrfmiddlewaretoken":
            continue
        posted[k] = post_data.getlist(k)

    question_keys = [k for k in posted if k.startswith("question_")]
    match_keys = [k for k in posted if k.startswith("match_")]

    # ==================================================
    # STANDARD QUESTION TYPES
    # ==================================================
    for qkey in question_keys:
        try:
            qid = int(qkey.split("_", 1)[1])
        except Exception:
            continue

        try:
            q = Question.objects.get(pk=qid)
        except Question.DoesNotExist:
            continue

        ua, _ = UserAnswer.objects.get_or_create(
            user_exam=ue,
            question=q
        )

        with transaction.atomic():
            ua = UserAnswer.objects.select_for_update().get(pk=ua.pk)
            vals = posted.get(qkey) or []

            # ----------------------------------------------
            # SINGLE / DROPDOWN / TRUE-FALSE
            # ----------------------------------------------
            if q.question_type in ("single", "dropdown", "tf"):
                if not vals:
                    continue

                try:
                    choice_id = int(str(vals[0]).strip())
                except Exception:
                    continue

                try:
                    ch = Choice.objects.get(pk=choice_id, question=q)
                except Choice.DoesNotExist:
                    continue

                ua.choice = ch
                ua.selections = None
                ua.raw_answer = None
                ua.is_correct = bool(ch.is_correct)
                ua.save()

            # ----------------------------------------------
            # MULTI SELECT
            # ----------------------------------------------
            elif q.question_type == "multi":
                sel_ids = []
                for v in vals:
                    try:
                        sel_ids.append(int(str(v).strip()))
                    except Exception:
                        pass

                ua.selections = sel_ids
                ua.choice = None
                ua.raw_answer = None
                ua.is_correct = None
                ua.save()

            # ----------------------------------------------
            # FILL / NUMERIC / ORDER
            # ----------------------------------------------
            elif q.question_type in ("fill", "numeric", "order"):
                raw = vals[0] if vals else ""
                ua.raw_answer = (raw or "").strip()
                ua.choice = None
                ua.selections = None
                ua.is_correct = None
                ua.save()

    # ==================================================
    # MATCH TYPE (KEYED INPUTS)
    # ==================================================
    if match_keys:
        match_by_q = {}

        for k in match_keys:
            parts = k.split("_")
            if len(parts) < 3:
                continue
            try:
                qid = int(parts[1])
                li = int(parts[2])
            except Exception:
                continue

            match_by_q.setdefault(qid, {})[li] = posted.get(k)[0] if posted.get(k) else ""

        for qid, mapping in match_by_q.items():
            try:
                q = Question.objects.get(pk=qid)
            except Question.DoesNotExist:
                continue

            ua, _ = UserAnswer.objects.get_or_create(
                user_exam=ue,
                question=q
            )

            with transaction.atomic():
                ua = UserAnswer.objects.select_for_update().get(pk=ua.pk)

                user_map = ua.selections or {}
                changed = False

                for li, val in mapping.items():
                    if not val:
                        if str(li) in user_map:
                            user_map.pop(str(li), None)
                            changed = True
                    else:
                        user_map[str(li)] = val
                        changed = True

                if changed:
                    ua.selections = user_map
                    ua.choice = None
                    ua.raw_answer = None
                    ua.is_correct = None
                    ua.save()
