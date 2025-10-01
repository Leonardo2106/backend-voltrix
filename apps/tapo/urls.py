from django.urls import path
from .views import get_dispositivo, get_dispositivo_energia, dispositivos

urlpatterns = [
    path('dispositivos/', dispositivos, name='tapo_dispositivos'),
    path('dispositivos/<int:pk>/energia/', get_dispositivo_energia, name='tapo_energia'),
]