from django.urls import path
from .views import ingest_energy, get_dispositivo_energia, dispositivos, energy_latest_cached

urlpatterns = [
    path('dispositivos/', dispositivos, name='tapo_dispositivos'),
    path('dispositivos/<int:pk>/energia/', get_dispositivo_energia, name='tapo_energia'),
    path('ingest/', ingest_energy),
    path('dispositivos/<int:device_id>/energia/latest-cached/', energy_latest_cached),
]