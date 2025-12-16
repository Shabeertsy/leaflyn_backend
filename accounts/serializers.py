from rest_framework import serializers
from .models import CompanyTransaction, UserPayment
from django.contrib.auth import get_user_model


User = get_user_model()



class CompanyTransactionSerializer(serializers.ModelSerializer):
    person = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = CompanyTransaction
        fields = [
            'id', 'transaction_type', 'amount', 'person', 'date_time',
            'split_amount', 'image', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'person']


class UserPaymentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    transaction = CompanyTransactionSerializer(read_only=True)

    class Meta:
        model = UserPayment
        fields = [
            'id', 'user', 'transaction', 'amount',
            'payment_date', 'payment_method', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'transaction']
