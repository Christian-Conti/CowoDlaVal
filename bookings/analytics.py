from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.apps import apps
from django.db.models import Q
from django.utils import timezone


CANCELLED_STATUSES = {"cancelled", "canceled", "deleted", "void", "abandoned"}
CONFIRMED_STATUSES = {"confirmed", "approved", "completed"}
PAID_STATUSES = {"paid", "completed", "succeeded", "success", "settled"}
UNFINISHED_PAYMENT_METHODS = {"", "unselected"}

WEEKDAYS_IT = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]


def _field_names(model) -> set[str]:
    return {field.name for field in model._meta.get_fields()}


def _as_date(value):
    if value is None:
        return None
    if hasattr(value, "date") and not isinstance(value, date):
        return value.date()
    return value


def _display(instance, field_name: str) -> str:
    getter = getattr(instance, f"get_{field_name}_display", None)
    if callable(getter):
        try:
            return str(getter())
        except Exception:
            pass
    return str(getattr(instance, field_name, "") or "—")


def _decimal(value) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except Exception:
        return Decimal("0")


def _date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _space_count() -> int:
    try:
        Space = apps.get_model("spaces", "Space")
    except LookupError:
        return 0

    qs = Space.objects.all()
    fields = _field_names(Space)
    for candidate in ("is_active", "active", "enabled"):
        if candidate in fields:
            qs = qs.filter(**{candidate: True})
            break
    return qs.count()


def get_booking_statistics(
    *,
    days: int | None = 30,
    start: date | None = None,
    end: date | None = None,
    all_time: bool = False,
) -> dict[str, Any]:
    """Compute booking analytics directly from the existing Booking model."""
    Booking = apps.get_model("bookings", "Booking")
    fields = _field_names(Booking)

    today = timezone.localdate()
    end = end or today

    if all_time:
        start = None
    elif start is None:
        days = max(int(days or 30), 1)
        start = end - timedelta(days=days - 1)

    qs = Booking.objects.all()

    related = [name for name in ("space", "user") if name in fields]
    if related:
        qs = qs.select_related(*related)

    # Do not count bookings that were created but never reached payment selection.
    if "payment_method" in fields:
        qs = qs.exclude(payment_method__in=list(UNFINISHED_PAYMENT_METHODS))

    # Select reservations overlapping the requested analysis period.
    if "date" in fields and start is not None:
        if "end_date" in fields:
            qs = qs.filter(
                Q(date__lte=end)
                & (Q(end_date__gte=start) | (Q(end_date__isnull=True) & Q(date__gte=start)))
            )
        else:
            qs = qs.filter(date__range=(start, end))
    elif "date" in fields:
        qs = qs.filter(date__lte=end)

    order = ["date"] if "date" in fields else []
    order.append("pk")
    rows = list(qs.order_by(*order))

    if all_time and rows and "date" in fields:
        dates = [_as_date(getattr(row, "date", None)) for row in rows]
        dates = [d for d in dates if d]
        effective_start = min(dates) if dates else today
    else:
        effective_start = start or today

    effective_end = end
    period_days = max((effective_end - effective_start).days + 1, 1)

    status_counter = Counter()
    payment_counter = Counter()
    method_counter = Counter()
    start_trend = Counter()
    occupied_trend = Counter()
    weekday_counter = Counter()
    user_counter = Counter()

    total = len(rows)
    confirmed = 0
    cancelled = 0
    paid_count = 0
    active_count = 0

    expected_revenue = Decimal("0")
    paid_revenue = Decimal("0")
    total_amount = Decimal("0")

    occupied_pairs = set()
    top_spaces = defaultdict(lambda: {"bookings": 0, "days": 0, "revenue": Decimal("0")})

    for booking in rows:
        status_raw = str(getattr(booking, "status", "") or "").strip().lower()
        status_label = _display(booking, "status") if "status" in fields else "—"
        status_counter[status_label] += 1

        is_cancelled = status_raw in CANCELLED_STATUSES
        if is_cancelled:
            cancelled += 1
        else:
            active_count += 1

        if status_raw in CONFIRMED_STATUSES:
            confirmed += 1

        payment_raw = str(getattr(booking, "payment_status", "") or "").strip().lower()
        if "payment_status" in fields:
            payment_counter[_display(booking, "payment_status")] += 1
        if "payment_method" in fields:
            method_counter[_display(booking, "payment_method")] += 1

        is_paid = payment_raw in PAID_STATUSES
        if is_paid:
            paid_count += 1

        amount = _decimal(getattr(booking, "amount", 0))
        total_amount += amount
        if not is_cancelled:
            expected_revenue += amount
        if is_paid and not is_cancelled:
            paid_revenue += amount

        user = getattr(booking, "user", None)
        user_id = getattr(user, "pk", None) if user is not None else None
        if user_id is not None:
            user_counter[user_id] += 1

        booking_start = _as_date(getattr(booking, "date", None))
        if booking_start is None:
            continue

        booking_end = _as_date(getattr(booking, "end_date", None)) or booking_start
        if booking_end < booking_start:
            booking_end = booking_start

        if effective_start <= booking_start <= effective_end:
            start_trend[booking_start] += 1
            weekday_counter[booking_start.weekday()] += 1

        if is_cancelled:
            continue

        clamped_start = max(booking_start, effective_start)
        clamped_end = min(booking_end, effective_end)
        if clamped_start > clamped_end:
            continue

        space = getattr(booking, "space", None)
        space_id = getattr(space, "pk", None)
        space_name = str(space) if space is not None else "Senza postazione"

        used_days = 0
        for day in _date_range(clamped_start, clamped_end):
            used_days += 1
            occupied_trend[day] += 1
            if space_id is not None:
                occupied_pairs.add((space_id, day))

        top_spaces[space_name]["bookings"] += 1
        top_spaces[space_name]["days"] += used_days
        top_spaces[space_name]["revenue"] += amount

    space_count = _space_count()
    capacity = space_count * period_days
    occupancy = (len(occupied_pairs) / capacity * 100.0) if capacity else None

    unique_users = len(user_counter)
    repeat_users = sum(1 for count in user_counter.values() if count > 1)
    repeat_rate = repeat_users / unique_users * 100.0 if unique_users else 0.0
    average_amount = total_amount / Decimal(total) if total else Decimal("0")
    cancellation_rate = cancelled / total * 100.0 if total else 0.0
    payment_rate = paid_count / active_count * 100.0 if active_count else 0.0

    trend = [
        {
            "date": day.isoformat(),
            "label": day.strftime("%d/%m"),
            "bookings": start_trend.get(day, 0),
            "occupied_desks": occupied_trend.get(day, 0),
        }
        for day in _date_range(effective_start, effective_end)
    ]

    peak = max(
        trend,
        key=lambda item: item["bookings"],
        default={"date": effective_start.isoformat(), "bookings": 0, "occupied_desks": 0},
    )

    top_space_rows = [
        {
            "space": name,
            "bookings": values["bookings"],
            "days": values["days"],
            "revenue": float(values["revenue"]),
        }
        for name, values in top_spaces.items()
    ]
    top_space_rows.sort(
        key=lambda item: (item["days"], item["bookings"], item["revenue"]), reverse=True
    )

    def counter_rows(counter):
        return [{"label": label, "count": count} for label, count in counter.most_common()]

    weekdays = [
        {"label": WEEKDAYS_IT[index], "count": weekday_counter.get(index, 0)}
        for index in range(7)
    ]

    return {
        "period": {
            "start": effective_start.isoformat(),
            "end": effective_end.isoformat(),
            "days": period_days,
            "all_time": bool(all_time),
        },
        "kpi": {
            "total": total,
            "active": active_count,
            "confirmed": confirmed,
            "cancelled": cancelled,
            "paid": paid_count,
            "unique_users": unique_users,
            "repeat_users": repeat_users,
            "repeat_rate": repeat_rate,
            "cancellation_rate": cancellation_rate,
            "payment_rate": payment_rate,
            "occupancy": occupancy,
            "space_count": space_count,
            "occupied_desk_days": len(occupied_pairs),
            "expected_revenue": float(expected_revenue),
            "paid_revenue": float(paid_revenue),
            "average_amount": float(average_amount),
            "peak_date": peak["date"],
            "peak_bookings": peak["bookings"],
        },
        "trend": trend,
        "weekdays": weekdays,
        "statuses": counter_rows(status_counter),
        "payment_statuses": counter_rows(payment_counter),
        "payment_methods": counter_rows(method_counter),
        "top_spaces": top_space_rows,
    }
