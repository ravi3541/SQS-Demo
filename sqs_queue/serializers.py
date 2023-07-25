from rest_framework import serializers


from .models import QueueModel


class QueueSerializer(serializers.ModelSerializer):
    """
    Class to create serializer Queue model.
    """

    class Meta:
        model = QueueModel
        fields = ("id", "queue_name", "attributes", "queue_url", "created_at", "updated_at")
