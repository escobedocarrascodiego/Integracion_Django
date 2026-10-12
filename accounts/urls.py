from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.views import MeView

urlpatterns = [
    # {"email", "password"} -> {"access", "refresh"}. The token carries only the
    # user id: anyone holding a JWT can read its payload, so no personal data goes in.
    path("login/", TokenObtainPairView.as_view(), name="login"),
    # {"refresh"} -> {"access"}: a new access token without typing the password again.
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
]
