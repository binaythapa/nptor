from django.apps import AppConfig
class QuizConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'quiz'

from django.apps import AppConfig

class QuizConfig(AppConfig):
    name = 'quiz'

    def ready(self):
        # import signals so they get registered
        import quiz.signals  # noqa: F401
