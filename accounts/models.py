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


