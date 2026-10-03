from django.apps import AppConfig


class ClassesConfig(AppConfig):
    name = 'apps.classes'

    def ready(self):
        from apps.classes import signals
