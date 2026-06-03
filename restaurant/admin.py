from django.contrib import admin

from .models import (
    InventoryItem,
    MenuItem,
    MenuItemIngredient,
    Order,
    OrderItem,
    Reservation,
    Table,
)


class MenuItemIngredientInline(admin.TabularInline):
    model = MenuItemIngredient
    extra = 1


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_available")
    list_filter = ("category", "is_available")
    search_fields = ("name", "description")
    inlines = [MenuItemIngredientInline]


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "quantity", "unit", "low_stock_threshold", "is_low_stock")
    search_fields = ("name",)


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("number", "capacity", "status")
    list_filter = ("status",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("unit_price",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "table", "customer_name", "status", "created_at", "total_amount")
    list_filter = ("status", "created_at")
    search_fields = ("customer_name",)
    inlines = [OrderItemInline]


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "customer_phone", "table", "party_size", "reservation_time", "status")
    list_filter = ("status", "reservation_time")
    search_fields = ("customer_name", "customer_phone")
