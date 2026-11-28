from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.db import models
from django.utils import timezone

from .validators import kyrgyz_phone_validator


class CustomUserManager(BaseUserManager):
    """Create users whose unique login identifier is their email address."""

    use_in_migrations = True

    def _create_user(self, email, password, phone_number="", **extra_fields):
        if not email:
            raise ValueError("Для создания пользователя необходимо указать email.")
        if not password:
            raise ValueError("Для создания пользователя необходимо указать пароль.")

        email = self.normalize_email(email.strip()).casefold()
        EmailValidator()(email)
        user = self.model(email=email, phone_number=phone_number or "", **extra_fields)
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, phone_number="", **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, phone_number, **extra_fields)

    def create_superuser(self, email, password=None, phone_number=None, **extra_fields):
        if not phone_number:
            raise ValueError("Для суперпользователя обязательно укажите номер телефона +996.")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперпользователь должен иметь is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперпользователь должен иметь is_superuser=True.")

        return self._create_user(email, password, phone_number, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("email", unique=True, validators=[EmailValidator()])
    phone_number = models.CharField(
        "номер телефона",
        max_length=13,
        blank=True,
        validators=[kyrgyz_phone_validator],
        help_text="Кыргызский номер в формате +996XXXXXXXXX; для суперпользователя обязателен.",
    )
    birthdate = models.DateField("дата рождения", null=True, blank=True)
    is_staff = models.BooleanField("доступ в админку", default=False)
    is_active = models.BooleanField("активен", default=True)
    date_joined = models.DateTimeField("дата регистрации", default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["phone_number"]

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"
        ordering = ["email"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(is_superuser=True, phone_number=""),
                name="superuser_phone_required",
            ),
        ]

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email.strip()).casefold()
        if self.is_superuser and not self.phone_number:
            raise ValidationError(
                {"phone_number": "Для суперпользователя обязательно укажите номер телефона +996."}
            )

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email.strip()).casefold()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.email
