import json
import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from orders.services.geolocation_service import GeolocationService

logger = logging.getLogger(__name__)


@require_POST
def reverse_geocode_api(request):
    """
    API endpoint for browser GPS coordinate conversion into delivery addresses.
    Expects latitude and longitude in POST body (JSON or form-data).
    """
    lat = None
    lon = None

    if request.content_type == "application/json":
        try:
            data = json.loads(request.body.decode("utf-8"))
            lat = data.get("latitude")
            lon = data.get("longitude")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse(
                {"success": False, "error": "Invalid JSON payload in request."},
                status=400,
            )
    else:
        lat = request.POST.get("latitude")
        lon = request.POST.get("longitude")

    if lat is None or lon is None:
        return JsonResponse(
            {"success": False, "error": "Both latitude and longitude parameters are required."},
            status=400,
        )

    result = GeolocationService.reverse_geocode(lat, lon)
    status_code = 200 if result.get("success") else 422
    return JsonResponse(result, status=status_code)
