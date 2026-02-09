from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.utils.timezone import now

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
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
        status["db"] = "error"
        status["error"] = str(e)
        return JsonResponse(status, status=500)

    # --- Cache check ---
    try:
        cache.set("health_check", "ok", timeout=10)
        if cache.get("health_check") != "ok":
            raise Exception("Cache read failed")
    except Exception as e:
        status["cache"] = "error"
        status["error"] = str(e)
        return JsonResponse(status, status=500)

    return JsonResponse(status, status=200)
