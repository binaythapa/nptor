import logging
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.utils.timezone import now

logger = logging.getLogger(__name__)


def health_check(request):
    status = {
        "status": "ok",
        "time": now().isoformat(),
        "db": "ok",
        "cache": "ok",
    }

    # --- DB check ---
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as e:
        logger.error("Health check DB check failed: %s", e)
        status["status"] = "error"
        status["db"] = "error"
        return JsonResponse(status, status=503)

    # --- Cache check ---
    try:
        cache.set("health_check", "ok", timeout=10)
        if cache.get("health_check") != "ok":
            raise Exception("Cache read failed")
    except Exception as e:
        logger.error("Health check Cache check failed: %s", e)
        status["status"] = "error"
        status["cache"] = "error"
        return JsonResponse(status, status=503)

    return JsonResponse(status, status=200)
