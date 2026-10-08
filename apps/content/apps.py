from django.apps import AppConfig


class ContentConfig(AppConfig):
    name = 'apps.content'

    def ready(self):
        from apps.content import signals
