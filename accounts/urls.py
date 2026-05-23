from django.urls import path
from .views import RegisterView, LoginView, LogoutView, MeView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/',    LoginView.as_view(),    name='login'),
    path('logout/',   LogoutView.as_view(),   name='logout'),
    path('me/',       MeView.as_view(),       name='me'),

    # Built-in SimpleJWT endpoint — silently refreshes access token
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]