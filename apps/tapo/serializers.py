from rest_framework import serializers
from .models import Dispositivo

"""
Serializer é utilizado para converter dados complexos, como objetos,
em um formato mais simples como JSON ou XML

Modelo[Dispositivo] (objeto) -> Serializer[Dispositivo] -> JSON

**Fácil para capturar no Frontend, sendo quase obrigatório**
"""

class DispositivoSerializer(serializers.ModelSerializer):
    class Meta:
        model=Dispositivo
        fields='__all__'

