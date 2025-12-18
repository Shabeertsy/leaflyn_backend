from django.db import models

from authentication.models import BaseModel
from django.contrib.auth import get_user_model


User = get_user_model()


class CompanyTransaction(BaseModel):
    TRANSACTION_TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]

    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES, db_index=True, verbose_name="Transaction Type")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Amount")
    person = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='company_transactions', verbose_name="Person", null=True, blank=True)
    date_time = models.DateTimeField(db_index=True, verbose_name="Date and Time")
    split_amount = models.BooleanField(default=False, verbose_name="Split Amount")
    image = models.ImageField(upload_to='transaction_images/', blank=True, null=True, verbose_name="Image")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    ADMIN_STATUS_CHOICES = [
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('new', 'New'),
    ]
    admin_status = models.CharField(max_length=10,choices=ADMIN_STATUS_CHOICES,default='new',db_index=True, verbose_name="Admin Status")

    class Meta:
        verbose_name = "Company Transaction"
        verbose_name_plural = "Company Transactions"
        ordering = ['-date_time']
        indexes = [
            models.Index(fields=['transaction_type']),
            models.Index(fields=['date_time']),
        ]

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} ({self.date_time.date()})"


class UserPayment(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments', verbose_name="User")
    transaction = models.ForeignKey(CompanyTransaction, on_delete=models.CASCADE, related_name='user_payments', verbose_name="Company Transaction")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Amount")
    payment_date = models.DateTimeField(auto_now_add=True, verbose_name="Payment Date")
    payment_method = models.CharField(max_length=50, verbose_name="Payment Method")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")

    class Meta:
        verbose_name = "User Payment"
        verbose_name_plural = "User Payments"
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['transaction']),
        ]

    def __str__(self):
        return f"{self.user} - {self.amount} ({self.payment_date.date()})"




## Client management and billing
class Client(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Client Name")
    email = models.EmailField(max_length=255, unique=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Phone Number")
    address = models.TextField(blank=True, null=True, verbose_name="Address")
    company_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Company Name")

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Service(BaseModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='services', verbose_name="Client")
    service_name = models.CharField(max_length=255, verbose_name="Service Name")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(blank=True, null=True, verbose_name="End Date")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Amount", default=0)
    is_closed = models.BooleanField(default=False, verbose_name="Is Closed")

    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.service_name} ({self.client.name})"


class ServiceTransaction(BaseModel):
    STATUS_CHOICES = [
        ('advance', 'Advance'),
        ('settled', 'Settled'),
        ('other', 'Other'),
    ]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='transactions', verbose_name="Service")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Amount")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='other', verbose_name="Status")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    transaction_date = models.DateTimeField(auto_now_add=True, verbose_name="Transaction Date")

    class Meta:
        verbose_name = "Service Transaction"
        verbose_name_plural = "Service Transactions"
        ordering = ['-transaction_date']

    def __str__(self):
        return f"{self.service} - {self.amount} ({self.get_status_display()})"
