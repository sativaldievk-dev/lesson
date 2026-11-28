from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from common.validators import validate_birthdate_from_token
from .models import Product

User = get_user_model()


class ProductModeratorPermissionTests(TestCase):
    password = "M0untain-River-2026!"

    def setUp(self):
        self.client = APIClient()
        self.moderator = User.objects.create_user(
            email="moderator@example.com", password=self.password, is_staff=True
        )
        self.owner = User.objects.create_user(email="owner@example.com", password=self.password)
        self.product = Product.objects.create(
            name="Owner's product",
            description="Created by someone else",
            price="12.50",
            created_by=self.owner,
        )
        self.list_url = reverse("product-list")
        self.detail_url = reverse("product-detail", args=[self.product.pk])

    def request(self, method, url, data=None):
        client_method = getattr(self.client, method)
        if method in ("get", "delete"):
            return client_method(url)
        return client_method(url, data, format="json")

    def test_staff_user_can_view_products(self):
        self.client.force_authenticate(self.moderator)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.product.pk)

    def test_moderator_can_put_another_users_product(self):
        self.client.force_authenticate(self.moderator)

        response = self.client.put(
            self.detail_url,
            {"name": "Revised product", "description": "Full update", "price": "15.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.created_by, self.owner)
        self.assertEqual(self.product.name, "Revised product")
        self.assertEqual(str(self.product.price), "15.00")

    def test_moderator_can_patch_another_users_product(self):
        self.client.force_authenticate(self.moderator)

        response = self.client.patch(self.detail_url, {"name": "Patched product"}, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.created_by, self.owner)
        self.assertEqual(self.product.name, "Patched product")

    def test_moderator_can_delete_another_users_product(self):
        self.client.force_authenticate(self.moderator)

        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_moderator_cannot_create_product(self):
        self.client.force_authenticate(self.moderator)

        response = self.client.post(
            self.list_url,
            {"name": "New product", "description": "Forbidden", "price": "10.00"},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Product.objects.count(), 1)

    def test_non_staff_user_does_not_have_moderator_permissions(self):
        self.client.force_authenticate(self.owner)

        for method, url, data in (
            ("get", self.list_url, None),
            ("put", self.detail_url, {"name": "No access", "description": "", "price": "1.00"}),
            ("patch", self.detail_url, {"name": "No access"}),
            ("delete", self.detail_url, None),
            ("post", self.list_url, {"name": "No access", "description": "", "price": "1.00"}),
        ):
            with self.subTest(method=method):
                response = self.request(method, url, data)
                self.assertEqual(response.status_code, 403)

        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_unauthenticated_user_cannot_access_protected_actions(self):
        for method, url, data in (
            ("get", self.list_url, None),
            ("put", self.detail_url, {"name": "No access", "description": "", "price": "1.00"}),
            ("patch", self.detail_url, {"name": "No access"}),
            ("delete", self.detail_url, None),
            ("post", self.list_url, {"name": "No access", "description": "", "price": "1.00"}),
        ):
            with self.subTest(method=method):
                response = self.request(method, url, data)
                self.assertEqual(response.status_code, 401)

        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())


class ProductCreateAgeTests(TestCase):
    password = "M0untain-River-2026!"

    def setUp(self):
        self.client = APIClient()
        self.create_url = reverse("product-list")
        self.product_data = {
            "name": "Allowed product",
            "description": "Created by an adult",
            "price": "10.00",
        }

    def authorize_with_token(self, user):
        response = self.client.post(
            "/api/token/",
            {"email": user.email, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_adult_can_create_product(self):
        user = User.objects.create_user(
            email="adult@example.com",
            password=self.password,
            birthdate=date(1990, 5, 12),
        )
        self.authorize_with_token(user)

        response = self.client.post(self.create_url, self.product_data, format="json")

        self.assertEqual(response.status_code, 201, response.data)
        product = Product.objects.get(pk=response.data["id"])
        self.assertEqual(product.created_by, user)

    def test_underage_user_cannot_create_product(self):
        today = timezone.localdate()
        user = User.objects.create_user(
            email="underage@example.com",
            password=self.password,
            birthdate=date(today.year - 17, today.month, today.day),
        )
        self.authorize_with_token(user)

        response = self.client.post(self.create_url, self.product_data, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            str(response.data["detail"]),
            "Вам должно быть 18 лет, чтобы создать продукт.",
        )
        self.assertFalse(Product.objects.exists())

    def test_token_without_birthdate_cannot_create_product(self):
        user = User.objects.create_user(email="missing@example.com", password=self.password)
        token = AccessToken.for_user(user)
        if "birthdate" in token:
            del token["birthdate"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")

        response = self.client.post(self.create_url, self.product_data, format="json")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            str(response.data["detail"]),
            "Укажите дату рождения, чтобы создать продукт.",
        )
        self.assertFalse(Product.objects.exists())

    def test_age_uses_month_and_day_not_only_birth_year(self):
        today = date(2026, 11, 28)

        self.assertEqual(
            validate_birthdate_from_token({"birthdate": "2008-11-28"}, today=today),
            date(2008, 11, 28),
        )
        with self.assertRaisesMessage(
            PermissionDenied,
            "Вам должно быть 18 лет, чтобы создать продукт.",
        ):
            validate_birthdate_from_token({"birthdate": "2008-11-29"}, today=today)
