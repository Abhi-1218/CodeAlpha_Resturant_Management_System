import json
from decimal import Decimal

from django.test import Client, TestCase

from .models import InventoryItem, MenuItem, MenuItemIngredient, Table


class RestaurantApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.table = Table.objects.create(number=1, capacity=4)
        self.cheese = InventoryItem.objects.create(
            name="Cheese",
            unit="kg",
            quantity=Decimal("2.00"),
            low_stock_threshold=Decimal("0.50"),
        )
        self.pizza = MenuItem.objects.create(
            name="Pizza",
            description="Cheese pizza",
            category="Main Course",
            price=Decimal("250.00"),
        )
        MenuItemIngredient.objects.create(
            menu_item=self.pizza,
            inventory_item=self.cheese,
            quantity_required=Decimal("0.25"),
        )

    def test_place_order_updates_table_and_inventory(self):
        response = self.client.post(
            "/api/orders/",
            data=json.dumps(
                {
                    "table_id": self.table.id,
                    "customer_name": "Test Customer",
                    "items": [{"menu_item_id": self.pizza.id, "quantity": 2}],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.table.refresh_from_db()
        self.cheese.refresh_from_db()
        self.assertEqual(self.table.status, Table.Status.OCCUPIED)
        self.assertEqual(self.cheese.quantity, Decimal("1.50"))
        self.assertEqual(response.json()["order"]["total_amount"], 500.0)

    def test_reservation_rejects_table_over_capacity(self):
        response = self.client.post(
            "/api/reservations/",
            data=json.dumps(
                {
                    "table_id": self.table.id,
                    "customer_name": "Large Group",
                    "customer_phone": "9999999999",
                    "party_size": 8,
                    "reservation_time": "2026-06-03T20:00:00+05:30",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
