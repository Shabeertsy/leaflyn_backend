from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

from django.core.exceptions import ValidationError
from authentication.models import BaseModel
from django.contrib.auth import get_user_model


User = get_user_model()



class PaymentGateway(models.Model):
    """Payment Gateway Configuration Model"""
    
    GATEWAY_CHOICES = [
        ('phonepe', 'PhonePe'),
        ('razorpay', 'Razorpay'),
        ('stripe', 'Stripe'),
        ('paytm', 'Paytm'),
        ('cashfree', 'Cashfree'),
    ]
    
    ENVIRONMENT_CHOICES = [
        ('sandbox', 'Sandbox/Test'),
        ('production', 'Production'),
    ]
    
    name = models.CharField(max_length=50, choices=GATEWAY_CHOICES, unique=True)
    display_name = models.CharField(max_length=100, help_text="Name shown to users")
    is_active = models.BooleanField(default=True, help_text="Enable/Disable this gateway")
    is_default = models.BooleanField(default=False, help_text="Set as default gateway")
    environment = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES, default='sandbox')
    
    # Gateway Credentials (stored as JSON for flexibility)
    credentials = models.JSONField(
        default=dict,
        help_text="Store gateway-specific credentials (encrypted in production)"
    )
    
    # Configuration
    configuration = models.JSONField(
        default=dict,
        help_text="Additional gateway-specific configuration",
        null=True,blank=True
    )
    
    # Ordering and display
    priority = models.IntegerField(
        default=0,
        help_text="Lower number = higher priority (0 is highest)"
    )
    logo = models.ImageField(upload_to='payment_gateways/', null=True, blank=True)
    description = models.TextField(blank=True)
    
    # Supported features
    supports_refund = models.BooleanField(default=True)
    supports_recurring = models.BooleanField(default=False)
    supports_upi = models.BooleanField(default=False)
    supports_cards = models.BooleanField(default=True)
    supports_netbanking = models.BooleanField(default=True)
    supports_wallets = models.BooleanField(default=False)
    
    # Limits
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    max_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Transaction fees
    transaction_fee_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        help_text="Gateway transaction fee %"
    )
    transaction_fee_fixed = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Fixed transaction fee amount"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_gateways'
    )
    
    class Meta:
        ordering = ['priority', 'display_name']
        verbose_name = 'Payment Gateway'
        verbose_name_plural = 'Payment Gateways'
    
    def __str__(self):
        status = "✓" if self.is_active else "✗"
        default = " (Default)" if self.is_default else ""
        return f"{status} {self.display_name}{default}"
    
    def clean(self):
        if self.is_default:
            existing_default = PaymentGateway.objects.filter(
                is_default=True
            ).exclude(pk=self.pk)
            if existing_default.exists():
                raise ValidationError(
                    "Another gateway is already set as default. "
                    "Please unset it first."
                )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def calculate_fee(self, amount):
        """Calculate transaction fee for given amount"""
        percentage_fee = amount * (self.transaction_fee_percentage / 100)
        total_fee = percentage_fee + self.transaction_fee_fixed
        return total_fee
    
    def is_amount_valid(self, amount):
        if amount < self.min_amount:
            return False
        if self.max_amount and amount > self.max_amount:
            return False
        return True


class PaymentGatewayLog(models.Model):
    
    gateway = models.ForeignKey(
        PaymentGateway, 
        on_delete=models.CASCADE, 
        related_name='logs'
    )
    payment = models.ForeignKey(
        'Payment', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    
    action = models.CharField(max_length=100)
    request_data = models.JSONField(null=True, blank=True)
    response_data = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=50)
    error_message = models.TextField(blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Gateway Log'
        verbose_name_plural = 'Gateway Logs'
    
    def __str__(self):
        return f"{self.gateway.name} - {self.action} - {self.status}"



PAYMENT_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
    ('refunded', 'Refunded'),
    ('initiated', 'Initiated'),
    ('cancelled', 'Cancelled'),
]

PAYMENT_METHOD_CHOICES = [
    ('phonepe', 'PhonePe'),
    ('razorpay', 'Razorpay'),
    ('paytm', 'Paytm'),
    ('upi', 'UPI'),
    ('card', 'Card'),
    ('netbanking', 'Net Banking'),
    ('wallet', 'Wallet'),
]

class Payment(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('999999.99'))]
    )

    # Generic foreign key for flexible payment associations
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    paid_for = GenericForeignKey('content_type', 'object_id')

    status = models.CharField(
        max_length=20,
        default='pending',
        choices=PAYMENT_STATUS_CHOICES,
        db_index=True
    )

    merchant_transaction_id = models.CharField(
        max_length=100,
        unique=True,
        default=uuid.uuid4,
        help_text="Unique merchant transaction ID for payment gateway"
    )

    payment_metadata = models.JSONField(
        default=dict,
        help_text="Additional payment information (customer details, order info, etc.)"
    )

    customer_phone = models.CharField(max_length=15, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_name = models.CharField(max_length=100, blank=True)

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='phonepe'
    )

    # Timestamps
    initiated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    gateway = models.ForeignKey(
        PaymentGateway,
        on_delete=models.PROTECT,
        related_name='payments',
        null=True,
        blank=True,
        help_text="Payment gateway used for this transaction"
    )

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['merchant_transaction_id']),
        ]

    def __str__(self):
        phone = getattr(self.user, 'phone_number', self.user.get_full_name())
        return f"{phone} - {self.status}"

    def save(self, *args, **kwargs):
        if not self.customer_name and self.user:
            self.customer_name = self.user.get_full_name() 

        if not self.customer_email and self.user:
            self.customer_email = self.user.email

        if hasattr(self.user, 'phone_number') and not self.customer_phone:
            self.customer_phone = self.user.phone_number

        from django.utils import timezone

        if self.status == 'initiated' and not self.initiated_at:
            self.initiated_at = timezone.now()
        elif self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status == 'failed' and not self.failed_at:
            self.failed_at = timezone.now()

        super().save(*args, **kwargs)

    @property
    def is_successful(self):
        return self.status == 'completed'

    @property
    def is_failed(self):
        return self.status == 'failed'

    @property
    def is_pending(self):
        return self.status in ['pending', 'initiated']

    @property
    def can_be_refunded(self):
        return self.status == 'completed' and not hasattr(self, 'refund_transaction')

    def get_display_amount(self):
        return f"₹{self.amount:,.2f}"



class Transaction(BaseModel):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='transactions')
    transaction_id = models.CharField(max_length=100, db_index=True)
    order_id = models.CharField(max_length=100, db_index=True)

    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES,
        default='phonepe'
    )

    gateway_response = models.JSONField(
        default=dict,
        help_text="Complete response from payment gateway"
    )

    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        db_index=True
    )

    phonepe_merchant_id = models.CharField(max_length=100, blank=True)
    phonepe_merchant_user_id = models.CharField(max_length=100, blank=True)
    phonepe_response_code = models.CharField(max_length=20, blank=True)
    phonepe_state = models.CharField(max_length=20, blank=True)
    payment_mode = models.CharField(max_length=50, blank=True, null=True)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Transaction amount (may differ from payment amount for partial payments)"
    )

    # Callback and verification details
    callback_received_at = models.DateTimeField(null=True, blank=True)
    verification_completed_at = models.DateTimeField(null=True, blank=True)
    checksum_verified = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment', 'status']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['order_id']),
            models.Index(fields=['created_at', 'status']),
        ]

    def __str__(self):
        return f"{self.payment} - {self.transaction_id}"

    def save(self, *args, **kwargs):
        if not self.amount and self.payment:
            self.amount = self.payment.amount

        if self.checksum_verified and not self.verification_completed_at:
            from django.utils import timezone
            self.verification_completed_at = timezone.now()

        super().save(*args, **kwargs)

    @property
    def is_successful(self):
        return self.status == 'completed'

    @property
    def phonepe_transaction_url(self):
        if self.transaction_id:
            return f"https://mercury.phonepe.com/transact/{self.transaction_id}"
        return None

    def get_gateway_data(self, key, default=None):
        """Safely get data from gateway response"""
        return self.gateway_response.get(key, default)


    def update_from_phonepe_response(self, response_data):
        self.gateway_response = response_data
        self.phonepe_state = response_data.get('state', '')
        self.phonepe_response_code = response_data.get('responseCode', '')
        self.phonepe_merchant_id = response_data.get('merchantId', '')
        self.phonepe_merchant_user_id = response_data.get('merchantUserId', '')

        phonepe_state = response_data.get('state', '').upper()
        response_code = response_data.get('responseCode', '').upper()

        print(f"Transaction update: phonepe_state={phonepe_state}, response_code='{response_code}'")

        if phonepe_state == 'COMPLETED':
            self.status = 'completed'
            print(f"Transaction {self.id} status updated to completed")
        elif phonepe_state == 'FAILED':
            self.status = 'failed'
            print(f"Transaction {self.id} status updated to failed")
        else:
            self.status = 'pending'
            print(f"Transaction {self.id} status remains pending")

        if not self.callback_received_at:
            from django.utils import timezone
            self.callback_received_at = timezone.now()

        self.save()
        print(f"Transaction {self.id} saved with status: {self.status}")


class RefundTransaction(BaseModel):

    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='refund_transaction'
    )

    original_transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='refund_transactions'
    )

    refund_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    phonepe_refund_id = models.CharField(max_length=100, blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    refund_reason = models.TextField()

    REFUND_STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    status = models.CharField(
        max_length=20,
        choices=REFUND_STATUS_CHOICES,
        default='initiated'
    )

    gateway_response = models.JSONField(default=dict)
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Refund Transaction"
        verbose_name_plural = "Refund Transactions"
        ordering = ['-created_at']

    def __str__(self):
        return f"Refund {self.refund_id} - ₹{self.refund_amount}"

    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.completed_at:
            from django.utils import timezone
            self.completed_at = timezone.now()
            self.payment.status = 'refunded'
            self.payment.save()
        super().save(*args, **kwargs)


class PaymentLog(BaseModel):

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='logs')
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, null=True, blank=True, related_name='logs')
    action = models.CharField(max_length=50, db_index=True)
    details = models.JSONField(default=dict)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    LOG_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]

    level = models.CharField(max_length=10, choices=LOG_LEVELS, default='info')

    class Meta:
        verbose_name = "Payment Log"
        verbose_name_plural = "Payment Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment', 'created_at']),
            models.Index(fields=['action', 'level']),
        ]

    def __str__(self):
        return f"{self.action} - {self.payment.merchant_transaction_id} - {self.created_at}"

    @classmethod
    def log_payment_event(cls, payment, action, details=None, user=None, ip_address=None, level='info'):
        """Convenience method to log payment events"""
        return cls.objects.create(
            payment=payment,
            action=action,
            details=details or {},
            user=user,
            ip_address=ip_address,
            level=level
        )