import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from orders.services.geolocation_service import GeolocationService

logger = logging.getLogger(__name__)


@csrf_exempt
def reverse_geocode_api(request):
    """
    API endpoint for browser GPS coordinate conversion into delivery addresses.
    Supports GET query parameters (?latitude=..&longitude=..) and POST (JSON or form).
    Does not modify database records or user state; purely a read-only translation utility.
    """
    lat = None
    lon = None

    if request.method == "GET":
        lat = request.GET.get("latitude") or request.GET.get("lat")
        lon = request.GET.get("longitude") or request.GET.get("lon")
    elif request.method == "POST":
        if request.content_type == "application/json":
            try:
                data = json.loads(request.body.decode("utf-8"))
                lat = data.get("latitude") or data.get("lat")
                lon = data.get("longitude") or data.get("lon")
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JsonResponse(
                    {"success": False, "error": "Invalid JSON payload in request."},
                    status=400,
                )
        else:
            lat = request.POST.get("latitude") or request.POST.get("lat")
            lon = request.POST.get("longitude") or request.POST.get("lon")
    else:
        return JsonResponse({"success": False, "error": "Method not allowed."}, status=405)

    if lat is None or lon is None:
        return JsonResponse(
            {"success": False, "error": "Both latitude and longitude parameters are required."},
            status=400,
        )

    result = GeolocationService.reverse_geocode(lat, lon)
    status_code = 200 if result.get("success") else 422
    return JsonResponse(result, status=status_code)
