from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    path('list/gateways/', views.ListPaymentGatewaysView.as_view(), name='list_gateways'),
    
    # Payment initiation
    path('initiate/', views.InitiatePaymentView.as_view(), name='initiate'),

    # PhonePe callbacks and status
    path('status/<str:merchant_transaction_id>/', views.UpdatedPaymentStatusView.as_view(), name='status'),
    path('status/', views.UpdatedPaymentStatusView.as_view(), name='status_generic'),

    # Payment management
    path('history/', views.PaymentHistoryView.as_view(), name='history'),
    path('detail/<str:merchant_transaction_id>/', views.PaymentDetailView.as_view(), name='detail'),
    path('dashboard/', views.PaymentDashboardView.as_view(), name='dashboard'),

    # Webhooks and utilities
    path('webhook/', views.payment_gateway_webhook, name='webhook'),
]