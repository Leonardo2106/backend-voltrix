from django.db import models
from django.contrib.auth.models import User

class Dispositivo(models.Model):

    """
    
    """

    uso_energia =       models.BooleanField(blank=None, null=None) # True "Hoje" | False "Este Mês"
    power =             models.BooleanField(blank=None, null=None)
    owner =             models.ForeignKey(User, on_delete=models.CASCADE, related_name='smart_device')
    title =             models.CharField(max_length=100, blank=None, null=None)
    local =             models.CharField(max_length=100, blank=None, null=None)
    definicao =         models.CharField(max_length=100, blank=None, null=None)
    tempo_exec =        models.CharField(max_length=10, blank=None, null=None)
    uso_ener =          models.CharField(max_length=10, blank=None, null=None)
    potencia_atual =    models.CharField(max_length=10, blank=None, null=None)

    def __str__(self):
        return self.title