from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import PaymentGateway, PaymentGatewayLog, Payment, Transaction, RefundTransaction, PaymentLog


@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    list_display = [
        'status_badge',
        'display_name',
        'name',
        'environment',
        'priority',
        'default_badge',
        'transaction_count',
        'total_amount',
        'actions_column'
    ]
    list_filter = ['is_active', 'is_default', 'environment', 'name']
    search_fields = ['display_name', 'name', 'description']
    ordering = ['priority', 'display_name']

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'display_name',
                'description',
                'logo',
                'is_active',
                'is_default',
                'priority'
            )
        }),
        ('Environment & Credentials', {
            'fields': (
                'environment',
                'credentials',
            ),
            'classes': ('collapse',),
            'description': 'Store credentials securely. Use environment variables in production.'
        }),
        ('Configuration', {
            'fields': (
                'configuration',
            ),
            'classes': ('collapse',),
        }),
        ('Features', {
            'fields': (
                'supports_refund',
                'supports_recurring',
                'supports_upi',
                'supports_cards',
                'supports_netbanking',
                'supports_wallets',
            ),
            'classes': ('collapse',),
        }),
        ('Limits & Fees', {
            'fields': (
                'min_amount',
                'max_amount',
                'transaction_fee_percentage',
                'transaction_fee_fixed',
            ),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">● Active</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">● Inactive</span>'
        )
    status_badge.short_description = 'Status'

    def default_badge(self, obj):
        if obj.is_default:
            return format_html(
                '<span style="background-color: #4CAF50; color: white; '
                'padding: 3px 8px; border-radius: 3px; font-size: 11px;">'
                'DEFAULT</span>'
            )
        return '-'
    default_badge.short_description = 'Default'

    def transaction_count(self, obj):
        count = obj.payments.count()
        if count > 0:
            url = reverse('admin:payment_payment_changelist') + f'?gateway__id__exact={obj.id}'
            return format_html(
                '<a href="{}">{} transactions</a>',
                url,
                count
            )
        return '0'
    transaction_count.short_description = 'Transactions'

    def total_amount(self, obj):
        from django.db.models import Sum
        total = obj.payments.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or 0
        return f"₹{total:,.2f}"
    total_amount.short_description = 'Total Revenue'

    def actions_column(self, obj):
        buttons = []

        # Test connection button
        buttons.append(
            f'<a class="button" href="#" onclick="testGateway({obj.id}); return false;">'
            'Test Connection</a>'
        )

        # View logs button
        log_url = reverse('admin:payment_paymentgatewaylog_changelist') + f'?gateway__id__exact={obj.id}'
        buttons.append(
            f'<a class="button" href="{log_url}">View Logs</a>'
        )

        return mark_safe(' '.join(buttons))
    actions_column.short_description = 'Actions'

    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    class Media:
        js = ('admin/js/gateway_admin.js',)
        css = {
            'all': ('admin/css/gateway_admin.css',)
        }


@admin.register(PaymentGatewayLog)
class PaymentGatewayLogAdmin(admin.ModelAdmin):
    list_display = [
        'created_at',
        'gateway',
        'action',
        'status_badge',
        'payment_link',
        'view_details'
    ]
    list_filter = [
        'gateway',
        'status',
        'action',
        'created_at'
    ]
    search_fields = [
        'action',
        'error_message',
        'payment__merchant_transaction_id'
    ]
    ordering = ['-created_at']
    readonly_fields = [
        'gateway',
        'payment',
        'action',
        'request_data',
        'response_data',
        'status',
        'error_message',
        'ip_address',
        'user_agent',
        'created_at'
    ]

    def status_badge(self, obj):
        colors = {
            'success': 'green',
            'completed': 'green',
            'failed': 'red',
            'error': 'red',
            'pending': 'orange',
        }
        color = colors.get(obj.status.lower(), 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status
        )
    status_badge.short_description = 'Status'

    def payment_link(self, obj):
        if obj.payment:
            url = reverse('admin:payment_payment_change', args=[obj.payment.id])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.payment.merchant_transaction_id
            )
        return '-'
    payment_link.short_description = 'Payment'

    def view_details(self, obj):
        return format_html(
            '<a class="button" href="{}">View</a>',
            reverse('admin:payment_paymentgatewaylog_change', args=[obj.id])
        )
    view_details.short_description = 'Details'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# Update existing Payment admin to show gateway
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'merchant_transaction_id',
        'user',
        'gateway_display',  
        'amount',
        'status',
        'created_at'
    ]
    list_filter = ['status', 'gateway', 'created_at']  

    def gateway_display(self, obj):
        if obj.gateway:
            return format_html(
                '<span style="background: #e3f2fd; padding: 2px 8px; '
                'border-radius: 3px;">{}</span>',
                obj.gateway.display_name
            )
        return format_html(
            '<span style="color: gray;">Not set</span>'
        )
    gateway_display.short_description = 'Gateway'

    # ... rest of existing PaymentAdmin code ... also add this


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'payment',
        'transaction_id',
        'amount',
        'payment_method',
        'status',
        'created_at',
        'phonepe_state',
    )
    list_filter = ('status', 'payment_method', 'created_at', 'phonepe_state')
    search_fields = (
        'transaction_id',
        'order_id',
        'payment__merchant_transaction_id',
        'payment__user__username',
        'payment__user__phone_number',
    )
    readonly_fields = (
        'created_at',
        'gateway_response',
        'callback_received_at',
        'verification_completed_at',
        'phonepe_state',
        'phonepe_response_code',
        'phonepe_merchant_id',
        'phonepe_merchant_user_id',
        'checksum_verified',
    )
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    raw_id_fields = ('payment',)


@admin.register(RefundTransaction)
class RefundTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'refund_id',
        'payment',
        'original_transaction',
        'refund_amount',
        'status',
        'requested_by',
        'created_at',
        'completed_at',
    )
    list_filter = ('status', 'created_at')
    search_fields = ('refund_id', 'payment__merchant_transaction_id', 'original_transaction__transaction_id')
    readonly_fields = (
        'refund_id',
        'phonepe_refund_id',
        'gateway_response',
        'created_at',
        'processed_at',
        'completed_at',
    )
    raw_id_fields = ('payment', 'original_transaction', 'requested_by')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'payment',
        'transaction',
        'action',
        'level',
        'user',
        'created_at',
        'ip_address',
    )
    list_filter = ('level', 'action', 'created_at')
    search_fields = (
        'action',
        'payment__merchant_transaction_id',
        'transaction__transaction_id',
        'user__username',
        'user__phone_number',
    )
    readonly_fields = (
        'created_at',
        'ip_address',
        'user_agent',
        'details',
    )
    raw_id_fields = ('payment', 'transaction', 'user')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
