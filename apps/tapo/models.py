from django.db import models
from django.contrib.auth.models import User

class Dispositivo(models.Model):
    owner           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='smart_device')
    title           = models.CharField(max_length=100, blank=True, null=True)
    local           = models.CharField(max_length=100, blank=True, null=True)
    definicao       = models.CharField(max_length=100, blank=True, null=True)

    uso_energia     = models.BooleanField(blank=True, null=True)   # True “Hoje” | False “Este Mês”
    power           = models.BooleanField(blank=True, null=True)   # ligado/desligado (estado desejado)
    tempo_exec      = models.CharField(max_length=10, blank=True, null=True)
    uso_ener        = models.CharField(max_length=10, blank=True, null=True)
    potencia_atual  = models.CharField(max_length=10, blank=True, null=True)

    ip              = models.CharField(max_length=100, blank=True, null=True)  # ex: "192.168.0.123"

    def __str__(self):
        return self.title or f'Dispositivo {self.pk}'
