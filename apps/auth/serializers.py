from rest_framework import serializers
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields=['email']

class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields=['id', 'username', 'email']

        def get_username(self, obj):
            return f'{obj.username}'.strip()
    
        def get_email(self, obj):
            return f'{obj.email}'.strip()


