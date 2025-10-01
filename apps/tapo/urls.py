from django.urls import path
from .views import get_dispositivo, get_dispositivo_energia

urlpatterns = [
    path('dispositivos/', get_dispositivo, name='tapo_listar_dispositivos'),
    path('dispositivos/<int:pk>/energia/', get_dispositivo_energia, name='tapo_energia'),
]