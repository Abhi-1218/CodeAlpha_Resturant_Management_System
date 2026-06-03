import json
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import F, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import InventoryItem, MenuItem, Order, Reservation, Table, today_sales_total


def home(request):
    return render(request, "restaurant/home.html")


def read_json(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        raise ValidationError("Invalid JSON body.")


def decimal_to_float(value):
    if isinstance(value, Decimal):
        return float(value)
    return value


def validation_error_response(error, status=400):
    if hasattr(error, "message_dict"):
        message = error.message_dict
    elif hasattr(error, "messages"):
        message = error.messages
    else:
        message = str(error)
    return JsonResponse({"error": message}, status=status)


@require_http_methods(["GET"])
def menu_list(request):
    items = MenuItem.objects.filter(is_available=True).order_by("category", "name")
    return JsonResponse(
        {
            "menu": [
                {
                    "id": item.id,
                    "name": item.name,
                    "description": item.description,
                    "category": item.category,
                    "price": decimal_to_float(item.price),
                }
                for item in items
            ]
        }
    )


@require_http_methods(["GET"])
def table_list(request):
    tables = Table.objects.order_by("number")
    return JsonResponse(
        {
            "tables": [
                {"id": table.id, "number": table.number, "capacity": table.capacity, "status": table.status}
                for table in tables
            ]
        }
    )


@require_http_methods(["GET"])
def available_tables(request):
    party_size = request.GET.get("party_size")
    tables = Table.objects.filter(status=Table.Status.AVAILABLE)
    if party_size:
        tables = tables.filter(capacity__gte=int(party_size))
    return JsonResponse(
        {
            "tables": [
                {"id": table.id, "number": table.number, "capacity": table.capacity, "status": table.status}
                for table in tables.order_by("number")
            ]
        }
    )


def serialize_order(order):
    return {
        "id": order.id,
        "table": order.table.number,
        "table_id": order.table_id,
        "customer_name": order.customer_name,
        "status": order.status,
        "created_at": order.created_at.isoformat(),
        "total_amount": decimal_to_float(order.total_amount),
        "items": [
            {
                "menu_item": item.menu_item.name,
                "quantity": item.quantity,
                "unit_price": decimal_to_float(item.unit_price),
                "line_total": decimal_to_float(item.line_total),
            }
            for item in order.items.select_related("menu_item")
        ],
    }


@require_http_methods(["GET"])
def order_list(request):
    orders = Order.objects.select_related("table").prefetch_related("items__menu_item").order_by("-created_at")[:50]
    return JsonResponse({"orders": [serialize_order(order) for order in orders]})


@csrf_exempt
@require_http_methods(["POST"])
def place_order(request):
    try:
        payload = read_json(request)
        table = Table.objects.get(pk=payload["table_id"])
        order = Order.place_order(
            table=table,
            items=payload.get("items", []),
            customer_name=payload.get("customer_name", ""),
        )
    except Table.DoesNotExist:
        return JsonResponse({"error": "Table not found."}, status=404)
    except (KeyError, TypeError, ValidationError) as error:
        return validation_error_response(error)

    return JsonResponse(
        {
            "message": "Order placed successfully.",
            "order": serialize_order(order),
        },
        status=201,
    )


@csrf_exempt
@require_http_methods(["PATCH", "PUT"])
def update_order(request, order_id):
    try:
        payload = read_json(request)
        order = Order.objects.select_related("table").get(pk=order_id)
        status = payload["status"]
        valid_statuses = [choice[0] for choice in Order.Status.choices]
        if status not in valid_statuses:
            raise ValidationError("Invalid order status.")
        order.status = status
        order.save(update_fields=["status", "updated_at"])
        if status in [Order.Status.PAID, Order.Status.CANCELLED]:
            Table.objects.filter(pk=order.table_id).update(status=Table.Status.AVAILABLE)
    except Order.DoesNotExist:
        return JsonResponse({"error": "Order not found."}, status=404)
    except (KeyError, ValidationError) as error:
        return validation_error_response(error)

    order.refresh_from_db()
    return JsonResponse({"message": "Order updated successfully.", "order": serialize_order(order)})


@csrf_exempt
@require_http_methods(["POST"])
def reserve_table(request):
    try:
        payload = read_json(request)
        table = Table.objects.get(pk=payload["table_id"])
        if table.status != Table.Status.AVAILABLE:
            raise ValidationError("Selected table is not available.")
        reservation = Reservation.objects.create(
            customer_name=payload["customer_name"],
            customer_phone=payload["customer_phone"],
            party_size=int(payload["party_size"]),
            table=table,
            reservation_time=payload["reservation_time"],
        )
    except Table.DoesNotExist:
        return JsonResponse({"error": "Table not found."}, status=404)
    except (KeyError, TypeError, ValueError, ValidationError) as error:
        return validation_error_response(error)

    return JsonResponse(
        {
            "message": "Table reserved successfully.",
            "reservation": {
                "id": reservation.id,
                "customer_name": reservation.customer_name,
                "table": reservation.table.number,
                "party_size": reservation.party_size,
                "reservation_time": reservation.reservation_time.isoformat(),
                "status": reservation.status,
            },
        },
        status=201,
    )


@require_http_methods(["GET"])
def inventory_list(request):
    items = InventoryItem.objects.order_by("name")
    return JsonResponse(
        {
            "inventory": [
                {
                    "id": item.id,
                    "name": item.name,
                    "unit": item.unit,
                    "quantity": decimal_to_float(item.quantity),
                    "low_stock_threshold": decimal_to_float(item.low_stock_threshold),
                    "is_low_stock": item.is_low_stock,
                }
                for item in items
            ]
        }
    )


@csrf_exempt
@require_http_methods(["PATCH", "PUT"])
def update_inventory(request, item_id):
    try:
        payload = read_json(request)
        item = InventoryItem.objects.get(pk=item_id)
        if "quantity" in payload:
            item.quantity = payload["quantity"]
        if "low_stock_threshold" in payload:
            item.low_stock_threshold = payload["low_stock_threshold"]
        if "unit" in payload:
            item.unit = payload["unit"]
        item.full_clean()
        item.save()
    except InventoryItem.DoesNotExist:
        return JsonResponse({"error": "Inventory item not found."}, status=404)
    except (ValidationError, ValueError) as error:
        return validation_error_response(error)

    return JsonResponse(
        {
            "message": "Inventory updated successfully.",
            "inventory_item": {
                "id": item.id,
                "name": item.name,
                "quantity": decimal_to_float(item.quantity),
                "unit": item.unit,
                "is_low_stock": item.is_low_stock,
            },
        }
    )


@require_http_methods(["GET"])
def daily_sales_report(request):
    report_date = request.GET.get("date")
    if report_date:
        all_orders = Order.objects.filter(created_at__date=report_date)
    else:
        all_orders = Order.objects.filter(created_at__date=timezone.localdate())

    paid_orders = all_orders.filter(status__in=[Order.Status.SERVED, Order.Status.PAID])
    all_order_items = all_orders.values("items__menu_item__name").annotate(
        quantity_sold=Sum("items__quantity"),
        revenue=Sum(F("items__quantity") * F("items__unit_price")),
    )
    paid_order_items = paid_orders.values("items__menu_item__name").annotate(
        quantity_sold=Sum("items__quantity"),
        revenue=Sum(F("items__quantity") * F("items__unit_price")),
    )
    total_order_value = sum(row["revenue"] or 0 for row in all_order_items)
    paid_sales = today_sales_total() if not report_date else sum(row["revenue"] or 0 for row in paid_order_items)

    return JsonResponse(
        {
            "date": report_date or timezone.localdate().isoformat(),
            "total_orders": all_orders.count(),
            "active_orders": all_orders.exclude(status__in=[Order.Status.PAID, Order.Status.CANCELLED]).count(),
            "total_order_value": decimal_to_float(total_order_value),
            "total_sales": decimal_to_float(paid_sales),
            "items": [
                {
                    "menu_item": row["items__menu_item__name"],
                    "quantity_sold": row["quantity_sold"],
                    "revenue": decimal_to_float(row["revenue"] or 0),
                }
                for row in all_order_items
            ],
        }
    )


@require_http_methods(["GET"])
def stock_alerts(request):
    items = InventoryItem.objects.filter(quantity__lte=F("low_stock_threshold")).order_by("quantity")
    return JsonResponse(
        {
            "alerts": [
                {
                    "id": item.id,
                    "name": item.name,
                    "quantity": decimal_to_float(item.quantity),
                    "unit": item.unit,
                    "low_stock_threshold": decimal_to_float(item.low_stock_threshold),
                }
                for item in items
            ]
        }
    )
