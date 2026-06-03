from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Sum
from django.utils import timezone


class Table(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        RESERVED = "reserved", "Reserved"
        OCCUPIED = "occupied", "Occupied"
        CLEANING = "cleaning", "Cleaning"

    number = models.PositiveIntegerField(unique=True)
    capacity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)

    def __str__(self):
        return f"Table {self.number} ({self.capacity} seats)"


class InventoryItem(models.Model):
    name = models.CharField(max_length=120, unique=True)
    unit = models.CharField(max_length=30, default="unit")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    low_stock_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=5)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"


class MenuItem(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    category = models.CharField(max_length=80, blank=True)
    is_available = models.BooleanField(default=True)
    ingredients = models.ManyToManyField(
        InventoryItem,
        through="MenuItemIngredient",
        related_name="menu_items",
        blank=True,
    )

    def __str__(self):
        return self.name


class MenuItemIngredient(models.Model):
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity_required = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("menu_item", "inventory_item")

    def __str__(self):
        return f"{self.menu_item} needs {self.quantity_required} {self.inventory_item.unit} {self.inventory_item}"


class Reservation(models.Model):
    class Status(models.TextChoices):
        BOOKED = "booked", "Booked"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    customer_name = models.CharField(max_length=120)
    customer_phone = models.CharField(max_length=30)
    table = models.ForeignKey(Table, on_delete=models.PROTECT, related_name="reservations")
    party_size = models.PositiveIntegerField()
    reservation_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BOOKED)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.party_size > self.table.capacity:
            raise ValidationError("Party size cannot exceed table capacity.")
        overlapping = Reservation.objects.filter(
            table=self.table,
            reservation_time__date=self.reservation_time.date(),
            status=Reservation.Status.BOOKED,
        )
        if self.pk:
            overlapping = overlapping.exclude(pk=self.pk)
        if overlapping.exists():
            raise ValidationError("This table already has a booking on that date.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        if self.status == Reservation.Status.BOOKED:
            Table.objects.filter(pk=self.table_id).update(status=Table.Status.RESERVED)

    def __str__(self):
        return f"{self.customer_name} - {self.table} at {self.reservation_time:%Y-%m-%d %H:%M}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PREPARING = "preparing", "Preparing"
        SERVED = "served", "Served"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    table = models.ForeignKey(Table, on_delete=models.PROTECT, related_name="orders")
    customer_name = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_amount(self):
        return self.items.aggregate(total=Sum(F("quantity") * F("unit_price")))["total"] or 0

    def __str__(self):
        return f"Order #{self.pk or 'new'} - Table {self.table.number}"

    @classmethod
    def place_order(cls, table, items, customer_name=""):
        if table.status not in [Table.Status.AVAILABLE, Table.Status.RESERVED, Table.Status.OCCUPIED]:
            raise ValidationError("Table is not available for orders.")

        with transaction.atomic():
            table = Table.objects.select_for_update().get(pk=table.pk)
            menu_item_ids = [item["menu_item_id"] for item in items]
            menu_items = {
                item.id: item
                for item in MenuItem.objects.prefetch_related("menuitemingredient_set").filter(
                    id__in=menu_item_ids,
                    is_available=True,
                )
            }

            if len(menu_items) != len(set(menu_item_ids)):
                raise ValidationError("One or more menu items are unavailable.")

            required_inventory = {}
            for item in items:
                menu_item = menu_items[item["menu_item_id"]]
                quantity = int(item["quantity"])
                if quantity <= 0:
                    raise ValidationError("Order quantity must be greater than zero.")
                for ingredient in menu_item.menuitemingredient_set.all():
                    required_inventory[ingredient.inventory_item_id] = (
                        required_inventory.get(ingredient.inventory_item_id, 0)
                        + ingredient.quantity_required * quantity
                    )

            inventory_items = {
                inv.id: inv for inv in InventoryItem.objects.select_for_update().filter(id__in=required_inventory)
            }
            for inventory_id, required_quantity in required_inventory.items():
                inventory_item = inventory_items[inventory_id]
                if inventory_item.quantity < required_quantity:
                    raise ValidationError(f"Not enough stock for {inventory_item.name}.")

            order = cls.objects.create(table=table, customer_name=customer_name)
            for item in items:
                menu_item = menu_items[item["menu_item_id"]]
                OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=int(item["quantity"]),
                    unit_price=menu_item.price,
                )

            for inventory_id, required_quantity in required_inventory.items():
                InventoryItem.objects.filter(pk=inventory_id).update(quantity=F("quantity") - required_quantity)

            table.status = Table.Status.OCCUPIED
            table.save(update_fields=["status"])
            return order


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name}"


def today_sales_total():
    today = timezone.localdate()
    return (
        OrderItem.objects.filter(order__created_at__date=today, order__status__in=[Order.Status.SERVED, Order.Status.PAID])
        .aggregate(total=Sum(F("quantity") * F("unit_price")))["total"]
        or 0
    )
