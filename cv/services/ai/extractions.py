from django.utils import timezone

from cv.models import AIExtraction


def confirm_ai_extraction(extraction_id, user, value=None):
    extraction = AIExtraction.objects.select_related("conversation").get(
        pk=extraction_id,
        conversation__owner=user,
    )
    if value is not None:
        extraction.proposed_value = value
    extraction.confirmed = True
    extraction.confirmed_by = user
    extraction.confirmed_at = timezone.now()
    extraction.save(update_fields=["proposed_value", "confirmed", "confirmed_by", "confirmed_at"])
    return extraction


def reject_ai_extraction(extraction_id, user):
    extraction = AIExtraction.objects.select_related("conversation").get(
        pk=extraction_id,
        conversation__owner=user,
    )
    extraction.confirmed = False
    extraction.confirmed_by = None
    extraction.confirmed_at = None
    extraction.save(update_fields=["confirmed", "confirmed_by", "confirmed_at"])
    return extraction
