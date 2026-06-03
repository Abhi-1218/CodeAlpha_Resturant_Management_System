from django.urls import path

from . import views

urlpatterns = [
    path("menu/", views.menu_list, name="menu-list"),
    path("tables/", views.table_list, name="table-list"),
    path("orders/", views.place_order, name="place-order"),
    path("orders/list/", views.order_list, name="order-list"),
    path("orders/<int:order_id>/", views.update_order, name="update-order"),
    path("tables/available/", views.available_tables, name="available-tables"),
    path("reservations/", views.reserve_table, name="reserve-table"),
    path("inventory/", views.inventory_list, name="inventory-list"),
    path("inventory/<int:item_id>/", views.update_inventory, name="update-inventory"),
    path("reports/daily-sales/", views.daily_sales_report, name="daily-sales-report"),
    path("reports/stock-alerts/", views.stock_alerts, name="stock-alerts"),
]
