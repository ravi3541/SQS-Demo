from django.urls import path
from .views import (
    CreateStandardQueueAPIView,
    SendMessageAPIView,
    ReceiveMessageAPIView,
    DeleteMessageAPIView,
    SetQueueAttributesAPIView,
    GetQueueUrlAPIView,
    DeleteQueueAPIView,
    ReceiveLambdaMessageAPIView,
)

urlpatterns = [
    path("createStandardQueue", CreateStandardQueueAPIView.as_view(), name="create-queue"),
    path("sendMessage/<int:pk>/", SendMessageAPIView.as_view(), name="send-message"),
    path("receiveMessage/<int:pk>/", ReceiveMessageAPIView.as_view(), name="receive-message"),
    path("deleteMessage/<int:pk>/", DeleteMessageAPIView.as_view(), name="delete-message"),
    path("setQueueAttrs/<int:pk>/", SetQueueAttributesAPIView.as_view(), name="set-queue-attributes"),
    path("getQueueUrl/<int:pk>/", GetQueueUrlAPIView.as_view(), name="get-queue-url"),
    path("deleteQueue/<int:pk>/", DeleteQueueAPIView.as_view(), name="delete-queue"),
    path("receiveLambdaMessage", ReceiveLambdaMessageAPIView.as_view(), name="receive-lambda-message"),

    # path("listQueues", ),
    # path("sendMessaageBatch", ),
    # path("deleteMessageBatch")
    # path("deleteQueue")

]
