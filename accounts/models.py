from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models


class UserManager(BaseUserManager):
    """Creates users identified by email instead of a username."""

    use_in_migrations = True

    def get_by_natural_key(self, email):
        # Login is case-insensitive: "Maria.Quispe@..." finds "maria.quispe@...".
        return self.get(email__iexact=email)

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The email must be set")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not (extra_fields["is_staff"] and extra_fields["is_superuser"]):
            raise ValueError("A superuser must have is_staff=True and is_superuser=True")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """A citizen who logs in with their email to check their own complaints.

    The DNI links citizens to their complaints. Staff accounts that only use the
    admin don't need one.
    """

    username = None
    email = models.EmailField("correo electrónico", unique=True)
    dni = models.CharField(
        "DNI",
        max_length=8,
        unique=True,
        null=True,
        blank=True,
        validators=[RegexValidator(r"^\d{8}$", "El DNI tiene 8 dígitos.")],
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # createsuperuser only asks for email and password

    objects = UserManager()

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return self.email
