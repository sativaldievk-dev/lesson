from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from rest_framework.test import APIClient

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
