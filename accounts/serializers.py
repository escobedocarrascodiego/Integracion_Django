from rest_framework import serializers

from accounts.models import User


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    class Meta:
        model = User
        fields = ["email", "full_name", "dni"]
