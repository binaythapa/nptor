from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"

    def ready(self):
        import accounts.signals
        from accounts.social_patch import patch_google_adapter

        patch_google_adapter()
