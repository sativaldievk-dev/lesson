from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price", "created_by", "created_at")
    search_fields = ("name", "created_by__email")
    list_select_related = ("created_by",)
