from rest_framework import generics

from accounts.serializers import UserProfileSerializer


class MeView(generics.RetrieveAPIView):
    """The logged-in user's profile (the default permission requires a login)."""

    serializer_class = UserProfileSerializer

    def get_object(self):
        # simplejwt loads the user from the database on every request, using the
        # id in the token: a deleted account stops working immediately.
        return self.request.user
