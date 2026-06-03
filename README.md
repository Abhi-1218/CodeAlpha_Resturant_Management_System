# Restaurant Management System

A Django backend for managing restaurant menu items, orders, tables, reservations, and inventory.

## Features

- Menu item API
- Table availability API
- Table reservation API
- Order placement API
- Inventory listing and update API
- Inventory auto-update when an order is placed
- Daily sales report
- Low stock alerts
- Django admin panel

## Setup

```bash
cd restaurant_management_system
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py seed_restaurant
python manage.py createsuperuser
python manage.py runserver
```

Admin panel:

```text
http://127.0.0.1:8000/admin/
```

API base URL:

```text
http://127.0.0.1:8000/api/
```

## API Endpoints

### View Menu

```http
GET /api/menu/
```

### Check Available Tables

```http
GET /api/tables/available/
GET /api/tables/available/?party_size=4
```

### Reserve Table

```http
POST /api/reservations/
Content-Type: application/json

{
  "customer_name": "Abhi",
  "customer_phone": "xxxxxxxxxx",
  "table_id": 1,
  "party_size": 4,
  "reservation_time": "2026-06-03T20:00:00+05:30"
}
```

### Place Order

```http
POST /api/orders/
Content-Type: application/json

{
  "table_id": 1,
  "customer_name": "Aakash",
  "items": [
    { "menu_item_id": 1, "quantity": 2 },
    { "menu_item_id": 2, "quantity": 1 }
  ]
}
```

When an order is placed, ingredient quantities linked to each menu item are automatically deducted from inventory.

### View Inventory

```http
GET /api/inventory/
```

### Update Inventory

```http
PATCH /api/inventory/1/
Content-Type: application/json

{
  "quantity": 25,
  "low_stock_threshold": 5,
  "unit": "kg"
}
```

### Daily Sales Report

```http
GET /api/reports/daily-sales/
GET /api/reports/daily-sales/?date=2026-06-03
```

### Stock Alerts

```http
GET /api/reports/stock-alerts/
```

## Suggested Admin Workflow

1. Create tables in the Django admin panel.
2. Create inventory items.
3. Create menu items and attach inventory ingredients with required quantities.
4. Use the reservation and order APIs for restaurant operations.
5. Use reports for daily sales and stock alerts.
