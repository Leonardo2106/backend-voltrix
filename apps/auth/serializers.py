from rest_framework import serializers
from django.contrib.auth.models import User

class UserRegistrationSerializers(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model=User
        fields=['username', 'email', 'password']

    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
        )

        user.set_password(validated_data['password'])
        user.save()

        return user

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


