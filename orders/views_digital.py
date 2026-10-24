import logging
from django.contrib.auth.decorators import login_required
from django.db import models
from django.http import FileResponse, Http404, HttpResponse

from orders.models import DigitalDelivery
from orders.services.digital_delivery_service import DigitalDeliveryService

logger = logging.getLogger(__name__)


@login_required
def download_digital_asset(request, download_token):
    """
    Secure file streaming view for purchased digital downloads.
    Guarantees:
    - User is authenticated and owns the purchase.
    - Master order is paid.
    - Token is neither expired, revoked, nor exceeded.
    - File is streamed securely without exposing physical paths or public URLs.
    """
    is_valid, reason, status_code, delivery = DigitalDeliveryService.claim_and_reserve_download(
        download_token=download_token,
        user=request.user,
    )

    if not is_valid:
        return HttpResponse(reason, status=status_code, content_type="text/plain")

    try:
        file_obj = delivery.digital_asset.file.open("rb")
    except (FileNotFoundError, ValueError, OSError) as exc:
        logger.error(f"Digital asset file not found on protected storage: {exc}")
        # Roll back download counter if file cannot be opened
        DigitalDelivery.objects.filter(id=delivery.id, download_count__gt=0).update(
            download_count=models.F("download_count") - 1
        )
        return HttpResponse("Digital file is currently unavailable. Please contact support.", status=404, content_type="text/plain")

    response = FileResponse(
        file_obj,
        as_attachment=True,
        filename=delivery.digital_asset.file_name,
        content_type="application/octet-stream",
    )
    # Prevent caching of protected downloads
    response["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response
