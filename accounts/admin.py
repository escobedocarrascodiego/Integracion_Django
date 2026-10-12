from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from accounts.models import User


# Django's stock user forms are tied to its default User (with a username),
# so the custom model needs its own.
class CitizenCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "dni")


class CitizenChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class CitizenAdmin(UserAdmin):
    form = CitizenChangeForm
    add_form = CitizenCreationForm
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "dni", "is_staff")
    search_fields = ("email", "first_name", "last_name", "dni")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "dni")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "dni", "password1", "password2")}),
    )
