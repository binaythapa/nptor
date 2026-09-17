from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class NPTORSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Keep the Google email address as the NPTOR username."""

    @staticmethod
    def _email_as_username(user):
        email = (getattr(user, "email", "") or "").strip().lower()
        if email:
            user.username = email

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        self._email_as_username(user)
        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        self._email_as_username(user)
        user.save(update_fields=["username"])
        return user
