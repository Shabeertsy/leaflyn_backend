from datetime import datetime, timedelta
from django.utils import timezone
from authentication.models import Profile
from user.models import Notification, Order


def global_data(request):
    now = timezone.now()
    last_week = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    # users last week
    new_users_last_week = Profile.objects.filter(
        created_at__gte=last_week,
        created_at__lt=now
    ).exclude(is_superuser=True).count()
    if not new_users_last_week:
        new_users_last_week = 0

    new_users_previous_week = Profile.objects.filter(
        created_at__gte=two_weeks_ago,
        created_at__lt=last_week
    ).exclude(is_superuser=True).count()
    if not new_users_previous_week:
        new_users_previous_week = 0

    if new_users_previous_week > 0:
        new_users_change_percentage = ((new_users_last_week - new_users_previous_week) / new_users_previous_week) * 100
    else:
        new_users_change_percentage = 100 if new_users_last_week > 0 else 0

    # Calculate orders for the last week
    orders_last_week = Order.objects.filter(
        created_at__gte=last_week,
        created_at__lt=now
    ).count()
    if not orders_last_week:
        orders_last_week = 0

    orders_previous_week = Order.objects.filter(
        created_at__gte=two_weeks_ago,
        created_at__lt=last_week
    ).count()
    if not orders_previous_week:
        orders_previous_week = 0

    if orders_previous_week > 0:
        orders_change_percentage = ((orders_last_week - orders_previous_week) / orders_previous_week) * 100
    else:
        orders_change_percentage = 100 if orders_last_week > 0 else 0

    dashboard_data = {
        "orders": orders_last_week,
        "orders_change": round(orders_change_percentage, 2) if orders_change_percentage is not None else 0,
        "orders_change_period": "Since last week",
        "orders_change_is_positive": (orders_change_percentage is not None and orders_change_percentage >= 0) or False,

        "new_users": new_users_last_week,
        "new_users_change": round(new_users_change_percentage, 2) if new_users_change_percentage is not None else 0,
        "new_users_change_period": "Since last week",
        "new_users_change_is_positive": (new_users_change_percentage is not None and new_users_change_percentage >= 0) or False,

        "sales": 924,  # example static value, replace with calculation or set to 0 as needed
        "sales_change": 1.10,
        "sales_change_period": "Since yesterday",
        "sales_change_is_positive": 1.10 >= 0,

        "performance": 49.65,
        "performance_change": 12,
        "performance_change_is_positive": 12 <= 0,
        "performance_change_period": "Since last month",
    }


    dashboard_notifications_qs = Notification.objects.filter().select_related("user").order_by('-created_at')
    dashboard_notifications = list(dashboard_notifications_qs[:5]) if dashboard_notifications_qs.exists() else []
    notification_count = dashboard_notifications_qs.filter(is_read=False).count()
    if not notification_count:
        notification_count = 0

    return {
        'site_name': 'Leafin Dashboard',
        'base_template': 'layouts/base.html',
        'logo': 'logo',
        'dashboard_data': dashboard_data,
        'dashboard_notifications': dashboard_notifications,
        'notification_count': notification_count,
    }
