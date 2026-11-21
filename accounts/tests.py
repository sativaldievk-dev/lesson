import os
from io import StringIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from rest_framework.test import APIClient
import yaml

from .admin import AdminUserCreationForm
from .serializers import RegisterSerializer

User = get_user_model()


class RegistrationAndLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "M0untain-River-2026!"

    def test_registration_without_phone_and_email_login(self):
        response = self.client.post(
            "/api/register/",
            {
                "email": "aliya@example.com",
                "password": self.password,
                "password_confirm": self.password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["email"], "aliya@example.com")
        self.assertEqual(response.data["phone_number"], "")

        user = User.objects.get(email="aliya@example.com")
        self.assertTrue(user.check_password(self.password))
        self.assertFalse(user.is_staff)

        response = self.client.post(
            "/api/login/",
            {"email": "ALIYA@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_registration_rejects_duplicate_email_and_password_mismatch(self):
        User.objects.create_user(email="aliya@example.com", password=self.password)
        duplicate = self.client.post(
            "/api/register/",
            {
                "email": "ALIYA@example.com",
                "password": self.password,
                "password_confirm": self.password,
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("email", duplicate.data)

        mismatch = self.client.post(
            "/api/register/",
            {
                "email": "other@example.com",
                "password": self.password,
                "password_confirm": "Different-Pass123!",
            },
            format="json",
        )
        self.assertEqual(mismatch.status_code, 400)
        self.assertIn("password_confirm", mismatch.data)

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(
            "/api/login/",
            {"email": "missing@example.com", "password": "incorrect"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.data)

    def test_invalid_phone_is_rejected_by_registration_api(self):
        response = self.client.post(
            "/api/register/",
            {
                "email": "bad-phone@example.com",
                "phone_number": "+99655512345",
                "password": self.password,
                "password_confirm": self.password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone_number", response.data)


class PhoneAndSuperuserTests(TestCase):
    def test_kyrgyz_phone_format_and_digit_count(self):
        valid = RegisterSerializer(
            data={
                "email": "valid@example.com",
                "phone_number": "+996555123456",
                "password": "M0untain-River-2026!",
                "password_confirm": "M0untain-River-2026!",
            }
        )
        self.assertTrue(valid.is_valid(), valid.errors)

        for phone in ("0555123456", "+99655512345", "+9965551234567", "+99655A123456"):
            with self.subTest(phone=phone):
                serializer = RegisterSerializer(
                    data={
                        "email": "bad-phone@example.com",
                        "phone_number": phone,
                        "password": "M0untain-River-2026!",
                        "password_confirm": "M0untain-River-2026!",
                    }
                )
                self.assertFalse(serializer.is_valid())
                self.assertIn("phone_number", serializer.errors)

    def test_superuser_requires_valid_phone(self):
        with self.assertRaisesMessage(ValueError, "обязательно"):
            User.objects.create_superuser(
                email="admin@example.com",
                password="M0untain-River-2026!",
            )

        with self.assertRaises(ValidationError):
            User.objects.create_superuser(
                email="bad-admin@example.com",
                password="M0untain-River-2026!",
                phone_number="+996123",
            )

        admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="M0untain-River-2026!",
            phone_number="+996555123456",
        )
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_staff)
        self.assertEqual(admin_user.phone_number, "+996555123456")

    def test_database_rejects_superuser_without_phone(self):
        with self.assertRaises(IntegrityError):
            User.objects.create(
                email="direct-admin@example.com",
                password="hashed-value",
                is_staff=True,
                is_superuser=True,
                phone_number="",
            )

    def test_createsuperuser_command_prompts_for_required_phone_field(self):
        password = "M0untain-River-2026!"
        output = StringIO()
        with patch.dict(os.environ, {"DJANGO_SUPERUSER_PASSWORD": password}):
            call_command(
                "createsuperuser",
                email="cli-admin@example.com",
                phone_number="+996555123456",
                interactive=False,
                stdout=output,
            )

        admin_user = User.objects.get(email="cli-admin@example.com")
        self.assertTrue(admin_user.is_superuser)
        self.assertEqual(admin_user.phone_number, "+996555123456")

    def test_admin_can_create_superuser_and_requires_phone(self):
        data = {
            "email": "admin@example.com",
            "phone_number": "",
            "password1": "M0untain-River-2026!",
            "password2": "M0untain-River-2026!",
            "is_active": True,
            "is_staff": True,
            "is_superuser": True,
        }
        form = AdminUserCreationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)

        data["phone_number"] = "+996555123456"
        form = AdminUserCreationForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        created = form.save()
        self.assertTrue(created.is_superuser)
        self.assertTrue(created.check_password(data["password1"]))


class JwtAndSwaggerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "M0untain-River-2026!"
        User.objects.create_user(email="aliya@example.com", password=self.password)

    def test_jwt_obtain_refresh_and_protected_api_authentication(self):
        unauthenticated = self.client.get("/api/me/")
        self.assertEqual(unauthenticated.status_code, 401)

        response = self.client.post(
            "/api/token/",
            {"email": "aliya@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        refresh_response = self.client.post(
            "/api/token/refresh/", {"refresh": response.data["refresh"]}, format="json"
        )
        self.assertEqual(refresh_response.status_code, 200, refresh_response.data)
        self.assertIn("access", refresh_response.data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh_response.data['access']}")
        protected = self.client.get("/api/me/")
        self.assertEqual(protected.status_code, 200)
        self.assertEqual(protected.data["email"], "aliya@example.com")

    def test_swagger_and_openapi_schema_include_auth_routes(self):
        docs = self.client.get("/api/docs/")
        self.assertEqual(docs.status_code, 200)
        self.assertContains(docs, "swagger-ui")

        schema = self.client.get("/api/schema/")
        self.assertEqual(schema.status_code, 200)
        schema_data = yaml.safe_load(schema.content)
        for route in (
            "/api/register/",
            "/api/login/",
            "/api/me/",
            "/api/token/",
            "/api/token/refresh/",
        ):
            self.assertIn(route, schema_data["paths"])

