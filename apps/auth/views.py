from django.contrib.auth.models import User
from django.conf import settings

from .serializers import (
    UserSerializer,
    UserRegistrationSerializers,
    MeSerializer,
)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

class CustomTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        try:
            base_response = super().post(request, *args, **kwargs) # {"access", "refresh"}
            tokens = base_response.data

            access_token =  tokens['access']
            refresh_token = tokens['refresh']

            res = Response(
                {'success': True, 'access': access_token, 'refresh': refresh_token},
                status=status.HTTP_200_OK
            )

            res.set_cookie(
                key='access_token',
                value=access_token,
                httponly=True,
                secure=getattr(settings, 'JWT_COOKIE_SECURE', False),
                samesite=getattr(settings, 'JWT_COOKIE_SAMESITE', 'None'),
                path='/'
            )
            res.set_cookie(
                key='refresh_token',
                value=refresh_token,
                httponly=True,
                secure=getattr(settings, 'JWT_COOKIE_SECURE', False),
                samesite=getattr(settings, 'JWT_COOKIE_SAMESITE', 'None'),
                path='/'
            )

            return res

        except Exception:
            return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)
        
class CustomTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh') or request.COOKIES.get('refresh_token')

        if not refresh_token:
            return Response({'detail': 'Refresh token ausente'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data={'refresh': refresh_token})

        try:
            serializer.is_valid(raise_exception = True)
        except (InvalidToken, TokenError):
            return Response({'refreshed': False}, status=status.HTTP_401_UNAUTHORIZED)
        
        access_token = serializer.validated_data['access']

        res = Response({'refreshed': False, 'access': access_token}, status=status.HTTP_200_OK)

        res.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            secure=getattr(settings, 'JWT_COOKIE_SECURE', False),
            samesite=getattr(settings, 'JWT_COOKIE_SAMESITE', 'None'),
            path='/',
        )

        return res
    
@api_view(['GET', 'PATH'])
@permission_classes([AllowAny])
def me(request):
    if request.method == 'GET':
        return Response(MeSerializer(request.user).data)
    
    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def is_authenticated(request):
    return Response({'authenticated': True})

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = UserRegistrationSerializers(data=request.data)
    if serializer.is_valid():
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def logout():
    try:
        res = Response({'success': True}, status=status.HTTP_200_OK)
        res.delete_cookie(
            key='access_token',
            samesite=getattr(settings, 'JWT_COOKIE_SAMESITE', 'None'),
            path='/',
        )
        res.delete_cookie(
            key='refresh_token',
            samesite=getattr(settings, 'JWT_COOKIE_SAMESITE', 'None'),
            path='/',
        )

        return res
    
    except Exception:
        return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)