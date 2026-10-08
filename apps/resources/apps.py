from django.apps import AppConfig


class ResourcesConfig(AppConfig):
    name = 'apps.resources'

    def ready(self):
        from apps.resources import signals