from decimal import Decimal

from django.core.management.base import BaseCommand

from restaurant.models import InventoryItem, MenuItem, MenuItemIngredient, Table


class Command(BaseCommand):
    help = "Create sample restaurant tables, inventory, menu items, and ingredient mappings."

    def handle(self, *args, **options):
        tables = [
            {"number": 1, "capacity": 2},
            {"number": 2, "capacity": 4},
            {"number": 3, "capacity": 4},
            {"number": 4, "capacity": 6},
        ]
        for table in tables:
            Table.objects.update_or_create(number=table["number"], defaults={"capacity": table["capacity"]})

        inventory_data = [
            ("Pizza Dough", "piece", "30", "8"),
            ("Cheese", "kg", "12", "3"),
            ("Tomato Sauce", "liter", "10", "2"),
            ("Pasta", "kg", "15", "4"),
            ("Vegetables", "kg", "20", "5"),
            ("Coffee Beans", "kg", "6", "2"),
        ]
        inventory = {}
        for name, unit, quantity, threshold in inventory_data:
            item, _ = InventoryItem.objects.update_or_create(
                name=name,
                defaults={
                    "unit": unit,
                    "quantity": Decimal(quantity),
                    "low_stock_threshold": Decimal(threshold),
                },
            )
            inventory[name] = item

        menu_data = [
            {
                "name": "Margherita Pizza",
                "category": "Main Course",
                "price": "249.00",
                "description": "Classic pizza with cheese and tomato sauce.",
                "ingredients": [("Pizza Dough", "1"), ("Cheese", "0.20"), ("Tomato Sauce", "0.15")],
            },
            {
                "name": "Veg Pasta",
                "category": "Main Course",
                "price": "199.00",
                "description": "Pasta tossed with vegetables and tomato sauce.",
                "ingredients": [("Pasta", "0.18"), ("Vegetables", "0.15"), ("Tomato Sauce", "0.10")],
            },
            {
                "name": "Cappuccino",
                "category": "Beverage",
                "price": "99.00",
                "description": "Hot coffee with steamed milk.",
                "ingredients": [("Coffee Beans", "0.03")],
            },
        ]

        for data in menu_data:
            menu_item, _ = MenuItem.objects.update_or_create(
                name=data["name"],
                defaults={
                    "category": data["category"],
                    "price": Decimal(data["price"]),
                    "description": data["description"],
                    "is_available": True,
                },
            )
            for inventory_name, quantity in data["ingredients"]:
                MenuItemIngredient.objects.update_or_create(
                    menu_item=menu_item,
                    inventory_item=inventory[inventory_name],
                    defaults={"quantity_required": Decimal(quantity)},
                )

        self.stdout.write(self.style.SUCCESS("Sample restaurant data created."))
