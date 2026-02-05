from django.conf import settings

def site_globals(request):
    return {
        "site_name": settings.SITE_NAME,
    }
