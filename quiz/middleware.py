# quiz/middleware.py
from django.shortcuts import redirect
from django.urls import reverse

EXEMPT_PATHS = [
    '/accounts/logout/',
    reverse('quiz:profile'),   # allow visiting profile to set email
    reverse('quiz:register'),
    reverse('login'),
    reverse('password_reset'),  # allow password reset pages, if desired
]

class EnsureEmailMiddleware:
    """
    If a logged in user has no email, force them to fill it on profile page.
    Exempt admin staff (optional) or specific paths.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        path = request.path
        # allow admin and staff to continue if desired:
        if user and user.is_authenticated and not user.email:
            # allow exempt paths and static media
            if any(path.startswith(p) for p in EXEMPT_PATHS) or path.startswith('/static/'):
                return self.get_response(request)
            # send to profile to add email
            return redirect(reverse('quiz:profile') + '?next=' + path)
        return self.get_response(request)
