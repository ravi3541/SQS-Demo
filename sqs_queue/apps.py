from django.apps import AppConfig


class SqsQueueConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sqs_queue'
