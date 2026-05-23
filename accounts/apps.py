from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Import signals here so they are registered when Django starts.
        # If you forget this, the signal functions exist but never fire.
        import accounts.signals  # noqa: F401