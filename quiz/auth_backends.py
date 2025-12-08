# quiz/auth_backends.py
import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

logger = logging.getLogger(__name__)
UserModel = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Robust backend that allows login by:
      - username (case-insensitive)
      - email (case-insensitive)
      - or using the model's USERNAME_FIELD (if different)
    It is defensive: uses filter(...).first() to avoid exceptions and supports
    being called with 'username' or 'email' or a generic 'identifier' kwarg.

    Returns a User instance when password matches and user_can_authenticate(user)
    is True. This should work immediately after user creation (no extra steps).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if password is None:
            return None

        # Support a generic 'identifier' kwarg (safe) or explicit 'email'
        identifier = username or kwargs.get('identifier') or kwargs.get('email')

        if not identifier:
            return None

        identifier = str(identifier).strip()

        # 1) Try exact username lookup based on the User model's USERNAME_FIELD
        username_field = getattr(UserModel, 'USERNAME_FIELD', 'username')
        user = None
        lookup = {f"{username_field}__iexact": identifier}
        user = UserModel.objects.filter(**lookup).first()

        # 2) Fallback: try email lookup (case-insensitive) if not found yet
        if user is None and hasattr(UserModel, 'email'):
            user = UserModel.objects.filter(email__iexact=identifier).first()

        # 3) If still None and kwargs contains 'pk' or 'user_id' try by id (edge-case)
        if user is None:
            pk = kwargs.get('pk') or kwargs.get('user_id') or kwargs.get('id')
            if pk:
                user = UserModel.objects.filter(pk=pk).first()

        if user is None:
            # No user found for identifier
            logger.debug("Auth backend: no user found for identifier=%s", identifier)
            return None

        # Verify password _after_ retrieving user. This should succeed for freshly created users too.
        try:
            if user.check_password(password) and self.user_can_authenticate(user):
                logger.debug("Auth backend: user %s authenticated via backend", getattr(user, username_field, user.pk))
                return user
            else:
                logger.debug("Auth backend: password mismatch or user cannot authenticate for %s", getattr(user, username_field, user.pk))
                return None
        except Exception as e:
            logger.exception("Auth backend error while checking password for user pk=%s: %s", getattr(user, 'pk', None), e)
            return None

    def get_user(self, user_id):
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
