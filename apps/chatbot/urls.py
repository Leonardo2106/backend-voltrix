from django.urls import path
from .views import ChatOnceView

urlpatterns = [
    path('chat/', ChatOnceView.as_view(), name='chatbot_chat'),
]
