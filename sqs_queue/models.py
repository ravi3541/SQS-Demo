from django.db import models


class QueueModel(models.Model):
    """
    Class to create model for storing queue details.
    """
    queue_name = models.CharField(max_length=80, null=False, blank=False)
    attributes = models.JSONField()
    queue_url = models.CharField(max_length=200, null=True, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
