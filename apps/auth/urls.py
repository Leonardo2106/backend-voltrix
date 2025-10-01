from django.urls import path

from .views import(
    logout, is_authenticated, me, register,
    CustomTokenObtainPairView, CustomTokenRefreshView,
)

urlpatterns = [
    path('logout/', logout),
    path('me/', me, name='me'),
    path('isauth/', is_authenticated),
    path('register/', register),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
]