import datetime
import json
import os
import boto3
from faker import Faker
from .models import QueueModel
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import (
    ListAPIView,
    CreateAPIView,
    GenericAPIView,
    DestroyAPIView,
    RetrieveAPIView,
)

from utilities import messages
from .serializers import QueueSerializer
from utilities.utils import ResponseInfo


Faker.seed(0)
fake = Faker()


class CreateStandardQueueAPIView(CreateAPIView):
    """
    Class to create API for creating SQS Queue.
    """
    permission_classes = ()
    authentication_classes = ()
    serializer_class = QueueSerializer

    def __init__(self, **kwargs):
        """
        Constructor function for formatting the web response to return.
        """
        self.response_format = ResponseInfo().response
        super(CreateStandardQueueAPIView, self).__init__(**kwargs)

    def post(self, request, *args, **kwargs):
        """
        Post method to create SQS Queue.
        """

        sqs = boto3.client(
            'sqs',
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        try:

            queue_name = request.data.get("queue_name")
            attributes = {
                "DelaySeconds": "0",          # 0-900 sec Default = 0
                "MaximumMessageSize": "262144",      # 1024-262144 Default = 262144(256 KiB)
                "MessageRetentionPeriod": "345600",         # 60-1,209,600 sec Default = 345600(4 days)
                "ReceiveMessageWaitTimeSeconds": "20",         # 0-20 sec Default 0
                "VisibilityTimeout": "43200"                  # 0-43200 sec Default 30 sec
            }

            response = sqs.create_queue(
                QueueName=queue_name,
                Attributes=attributes
            )
            if response.get("ResponseMetadata").get("HTTPStatusCode", None) == 200:
                serializer_data = {
                    "queue_name": queue_name,
                    "attributes": attributes,
                    "queue_url": response.get("QueueUrl", None)
                }
                queue_serializer = self.get_serializer(data=serializer_data)
                if queue_serializer.is_valid(raise_exception=True):
                    queue_serializer.save()
                    response["queue_object"] = queue_serializer.data

                self.response_format["status_code"] = status.HTTP_201_CREATED
                self.response_format["data"] = response
                self.response_format["error"] = None
                self.response_format["message"] = [messages.CREATED.format("SQS Queue")]

        except sqs.exceptions.QueueDeletedRecently:
            self.response_format["status_code"] = status.HTTP_404_NOT_FOUND
            self.response_format["data"] = None
            self.response_format["error"] = "Queue"
            self.response_format["message"] = [messages.QUEUE_RECENTLY_DELETED]

        except sqs.exceptions.QueueNameExists:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "Queue creation"
            self.response_format["message"] = [messages.QUEUE_EXIST]

        return Response(self.response_format)


class SendMessageAPIView(CreateAPIView):
    """
    Class to create API to send message to queue.
    """
    permission_classes = ()
    authentication_classes = ()

    def __init__(self, **kwargs):
        """
        Constructor function for formatting the web response to return.
        """
        self.response_format = ResponseInfo().response
        super(SendMessageAPIView, self).__init__(**kwargs)

    def get_queryset(self):
        queue_id = self.kwargs["pk"]
        return QueueModel.objects.get(id=queue_id)

    def post(self, request, *args, **kwargs):
        """
        Post method to send message to queue.
        """
        sqs = boto3.client(
            'sqs',
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        try:
            queue = self.get_queryset()

            message = {
                "order_id": str(fake.random_number(digits=7)),
                "order_date": fake.date(),
                "total_value": fake.random_number(digits=4),
                "status": "ORDER_PLACED",
                "sequence_id": request.data.get("sequence_id")
            }

            response = sqs.send_message(
                QueueUrl=queue.queue_url,
                MessageBody=json.dumps(message),
                DelaySeconds=10,
            )
            if response.get("ResponseMetadata").get("HTTPStatusCode", None) == 200:

                self.response_format["status_code"] = status.HTTP_201_CREATED
                self.response_format["data"] = response
                self.response_format["error"] = None
                self.response_format["message"] = [messages.MESSAGE_SENT]

        except sqs.exceptions.InvalidMessageContents:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "Message"
            self.response_format["message"] = [messages.INVALID_MESSAGE_CONTENT]

        except sqs.exceptions.UnsupportedOperation:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "Message"
            self.response_format["message"] = [messages.UNSUPPORTED_OPERATION]

        except QueueModel.DoesNotExist:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "Queue Object"
            self.response_format["message"] = [messages.DOES_NOT_EXIST.format("Queue")]

        return Response(self.response_format)


class ReceiveMessageAPIView(RetrieveAPIView):
    """
    Class to create API to receive messages from queue.
    """
    permission_classes = ()
    authentication_classes = ()

    def __init__(self, **kwargs):
        """
        Constructor function for formatting the web response to return.
        """
        self.response_format = ResponseInfo().response
        super(ReceiveMessageAPIView, self).__init__(**kwargs)

    def get_queryset(self):
        queue_id = self.kwargs["pk"]
        return QueueModel.objects.get(id=queue_id)

    def get(self, request, *args, **kwargs):
        """
        Get method for polling messages from queue.
        """

        sqs = boto3.client(
            'sqs',
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        try:
            queue = self.get_queryset()

            response = sqs.receive_message(
                QueueUrl=queue.queue_url,
                AttributeNames=[
                    'Policy', 'VisibilityTimeout', 'MaximumMessageSize', 'MessageRetentionPeriod',
                    'ApproximateNumberOfMessages', 'CreatedTimestamp', 'LastModifiedTimestamp',
                    'QueueArn', 'DelaySeconds', 'ReceiveMessageWaitTimeSeconds'
                ],
                MaxNumberOfMessages=10,
                VisibilityTimeout=20,
                WaitTimeSeconds=10,
            )
            if response.get("ResponseMetadata").get("HTTPStatusCode", None) == 200:

                self.response_format["status_code"] = status.HTTP_200_OK
                self.response_format["data"] = response
                self.response_format["error"] = None
                self.response_format["message"] = [messages.SUCCESS]
                if response.get("Messages", None) is None:
                    self.response_format["data"] = None
                    self.response_format["message"] = [messages.NO_MESSAGES]

        except sqs.exceptions.OverLimit:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "Message"
            self.response_format["message"] = [messages.INVALID_MESSAGE_CONTENT]

        except QueueModel.DoesNotExist:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "Queue Object"
            self.response_format["message"] = [messages.DOES_NOT_EXIST.format("Queue")]

        return Response(self.response_format)


class DeleteMessageAPIView(DestroyAPIView):
    """
    Class to create API for deleting messages from queue.
    """
    permission_classes = ()
    authentication_classes = ()

    def __init__(self, **kwargs):
        """
        Constructor function for formatting the web response to return.
        """
        self.response_format = ResponseInfo().response
        super(DeleteMessageAPIView, self).__init__(**kwargs)

    def get_queryset(self):
        queue_id = self.kwargs["pk"]
        return QueueModel.objects.get(id=queue_id)

    def delete(self, request, *args, **kwargs):
        """
        Delete method to delete messages from queue.
        """
        sqs = boto3.client(
            'sqs',
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        try:
            queue = self.get_queryset()

            response = sqs.receive_message(
                QueueUrl=queue.queue_url,
                AttributeNames=[
                    'Policy', 'VisibilityTimeout', 'MaximumMessageSize', 'MessageRetentionPeriod', 'ApproximateNumberOfMessages', 'CreatedTimestamp', 'LastModifiedTimestamp', 'QueueArn', 'DelaySeconds', 'ReceiveMessageWaitTimeSeconds'
                ],
                MaxNumberOfMessages=10,
                VisibilityTimeout=20,
                WaitTimeSeconds=10,
            )

            if response.get("ResponseMetadata").get("HTTPStatusCode", None) == 200:
                if len(response.get("Messages", [])) > 0:
                    message = response.get("Messages")[0]

                    delete_response = sqs.delete_message(
                        QueueUrl=queue.queue_url,
                        ReceiptHandle=message.get("ReceiptHandle")
                    )
                    if delete_response:
                        self.response_format["status_code"] = status.HTTP_201_CREATED
                        self.response_format["data"] = delete_response
                        self.response_format["error"] = None
                        self.response_format["message"] = [messages.DELETED.format("Message")]
                    else:
                        self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
                        self.response_format["data"] = None
                        self.response_format["error"] = "SQS"
                        self.response_format["message"] = [messages.SQS_UNEXPECTED]
                else:
                    self.response_format["status_code"] = status.HTTP_404_NOT_FOUND
                    self.response_format["data"] = None
                    self.response_format["error"] = "Messages"
                    self.response_format["message"] = [messages.NOT_FOUND.format("Messages")]

        except sqs.exceptions.InvalidIdFormat:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "Message"
            self.response_format["message"] = [messages.INVALID_MESSAGE_CONTENT]

        except sqs.exceptions.ReceiptHandleIsInvalid:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "ReceiptHandle"
            self.response_format["message"] = [messages.INVALID.format("ReceiptHandle")]

        except QueueModel.DoesNotExist:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "Queue Object"
            self.response_format["message"] = [messages.DOES_NOT_EXIST.format("Queue")]

        return Response(self.response_format)


class SetQueueAttributesAPIView(GenericAPIView):
    """
    Class to create API to set queue attributes.
    """
    permission_classes = ()
    authentication_classes = ()

    def __init__(self, **kwargs):
        """
        Constructor function for formatting the web response to return.
        """
        self.response_format = ResponseInfo().response
        super(SetQueueAttributesAPIView, self).__init__(**kwargs)

    def get_queryset(self):
        queue_id = self.kwargs["pk"]
        return QueueModel.objects.get(id=queue_id)

    def patch(self, request, *args, **kwargs):
        """
        Patch method to set queue attributes.
        """

        sqs = boto3.client(
            'sqs',
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        try:
            queue = self.get_queryset()

            attributes = {
                "DelaySeconds": "20",
                "MaximumMessageSize": "12800",  # 100Kib
                "MessageRetentionPeriod": "172800",  # 2 days
                "ReceiveMessageWaitTimeSeconds": "10",
                "VisibilityTimeout": "60"
            }

            response = sqs.set_queue_attributes(
                    QueueUrl=queue.queue_url,
                    Attributes=attributes
                )

            if response.get("ResponseMetadata").get("HTTPStatusCode", None) == 200:

                self.response_format["status_code"] = status.HTTP_201_CREATED
                self.response_format["data"] = response
                self.response_format["error"] = None
                self.response_format["message"] = [messages.DELETED.format("Message")]
            else:
                self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
                self.response_format["data"] = None
                self.response_format["error"] = "SQS"
                self.response_format["message"] = [messages.SQS_UNEXPECTED]

        except sqs.exceptions.InvalidIdFormat:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "Message"
            self.response_format["message"] = [messages.INVALID_MESSAGE_CONTENT]

        except sqs.exceptions.ReceiptHandleIsInvalid:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "ReceiptHandle"
            self.response_format["message"] = [messages.INVALID.format("ReceiptHandle")]

        except QueueModel.DoesNotExist:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "Queue Object"
            self.response_format["message"] = [messages.DOES_NOT_EXIST.format("Queue")]

        return Response(self.response_format)


class GetQueueUrlAPIView(GenericAPIView):
    """
    Class to create API to get queue url.
    """
    permission_classes = ()
    authentication_classes = ()

    def __init__(self, **kwargs):
        """
        Constructor function for formatting the web response to return.
        """
        self.response_format = ResponseInfo().response
        super(GetQueueUrlAPIView, self).__init__(**kwargs)

    def get_queryset(self):
        queue_id = self.kwargs["pk"]
        return QueueModel.objects.get(id=queue_id)

    def get(self, request, *args, **kwargs):
        """
        Get method to get queue url.
        """

        sqs = boto3.client(
            'sqs',
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        try:
            queue = self.get_queryset()

            response = sqs.get_queue_url(QueueName=queue.queue_name)

            if response.get("ResponseMetadata").get("HTTPStatusCode", None) == 200:

                self.response_format["status_code"] = status.HTTP_200_OK
                self.response_format["data"] = response
                self.response_format["error"] = None
                self.response_format["message"] = [messages.SUCCESS]
            else:
                self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
                self.response_format["data"] = None
                self.response_format["error"] = "SQS"
                self.response_format["message"] = [messages.SQS_UNEXPECTED]

        except sqs.exceptions.QueueDoesNotExist:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "SQS Queue"
            self.response_format["message"] = [messages.DOES_NOT_EXIST.format("SQS Queue")]

        except QueueModel.DoesNotExist:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "Queue Object"
            self.response_format["message"] = [messages.DOES_NOT_EXIST.format("Queue")]

        return Response(self.response_format)


class DeleteQueueAPIView(GenericAPIView):
    """
    Class to create API to delete queue.
    """
    permission_classes = ()
    authentication_classes = ()

    def __init__(self, **kwargs):
        """
        Constructor function for formatting the web response to return.
        """
        self.response_format = ResponseInfo().response
        super(DeleteQueueAPIView, self).__init__(**kwargs)

    def get_queryset(self):
        queue_id = self.kwargs["pk"]
        return QueueModel.objects.get(id=queue_id)

    def delete(self, request, *args, **kwargs):
        """
        Delete method to delete queue.
        """
        sqs = boto3.client(
            'sqs',
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        try:
            queue = self.get_queryset()

            response = sqs.delete_queue(QueueUrl=queue.queue_url)

            if response.get("ResponseMetadata").get("HTTPStatusCode", None) == 200:
                queue.delete()

                self.response_format["status_code"] = status.HTTP_200_OK
                self.response_format["data"] = response
                self.response_format["error"] = None
                self.response_format["message"] = [messages.SUCCESS]
            else:
                self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
                self.response_format["data"] = None
                self.response_format["error"] = "SQS"
                self.response_format["message"] = [messages.SQS_UNEXPECTED]

        except sqs.exceptions.QueueDoesNotExist:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "SQS Queue"
            self.response_format["message"] = [messages.DOES_NOT_EXIST.format("SQS Queue")]

        except QueueModel.DoesNotExist:
            self.response_format["status_code"] = status.HTTP_400_BAD_REQUEST
            self.response_format["data"] = None
            self.response_format["error"] = "Queue Object"
            self.response_format["message"] = [messages.DOES_NOT_EXIST.format("Queue")]

        return Response(self.response_format)


class ReceiveLambdaMessageAPIView(CreateAPIView):
    """
    Class to create API to receive messages from queue.
    """
    permission_classes = ()
    authentication_classes = ()

    def __init__(self, **kwargs):
        """
        Constructor function for formatting the web response to return.
        """
        self.response_format = ResponseInfo().response
        super(ReceiveLambdaMessageAPIView, self).__init__(**kwargs)

    def get_queryset(self):
        queue_id = self.kwargs["pk"]
        return QueueModel.objects.get(id=queue_id)

    def post(self, request, *args, **kwargs):
        """
        Get method for polling messages from queue.
        """

        print(request.data, datetime.datetime.now())
        print("step - 1")
        import time
        time.sleep(60)
        print("step - 2")
        return Response(self.response_format)
