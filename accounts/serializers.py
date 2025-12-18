from rest_framework import serializers
from .models import CompanyTransaction, UserPayment
from django.contrib.auth import get_user_model
from django.db.models import Sum



User = get_user_model()



class UserShortSerializer(serializers.ModelSerializer):
    person_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'person_name']

    def get_person_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()



class CompanyTransactionSerializer(serializers.ModelSerializer):
    person = UserShortSerializer(read_only=True)
    is_closed = serializers.SerializerMethodField()
    total_split_amount = serializers.SerializerMethodField()
    total_received_amount = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()

    class Meta:
        model = CompanyTransaction
        fields = [
            'id', 'transaction_type', 'amount', 'person', 'date_time',
            'split_amount', 'image', 'notes', 'created_at', 'updated_at', 'is_closed',
            'total_split_amount', 'total_received_amount', 'remaining_amount'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'person', 'is_closed',
            'total_split_amount', 'total_received_amount', 'remaining_amount'
        ]

    def get_is_closed(self, obj):
        payments_sum = UserPayment.objects.filter(transaction=obj).aggregate(total=Sum('amount'))['total'] or 0
        return payments_sum >= obj.amount
        
    def get_number_of_partners(self, obj):
        return User.objects.filter(user_type='partner').count()

    def get_total_split_amount(self, obj):
        if obj.split_amount:
            number_of_partners = self.get_number_of_partners(obj)
            if number_of_partners > 0:
                return round(float(obj.amount) / number_of_partners, 2)
            return 0.0
        return 0.0


    def get_total_received_amount(self, obj):
        payments_sum = UserPayment.objects.filter(transaction=obj).aggregate(total=Sum('amount'))['total'] or 0
        return float(payments_sum)

    def get_remaining_amount(self, obj):
        payments_sum = UserPayment.objects.filter(transaction=obj).aggregate(total=Sum('amount'))['total'] or 0
        remaining = float(obj.amount) - float(payments_sum)
        return max(0, remaining)


class CompanyTransactionForPartnerSerializer(serializers.ModelSerializer):
    person = serializers.StringRelatedField(read_only=True)
    is_closed = serializers.SerializerMethodField()

    class Meta:
        model = CompanyTransaction
        fields = [
            'id', 'transaction_type', 'amount', 'person', 'date_time',
            'split_amount', 'image', 'notes', 'created_at', 'updated_at', 'is_closed'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'person', 'is_closed']

    def get_is_closed(self, obj):
        payments_sum = UserPayment.objects.filter(transaction=obj).aggregate(total=Sum('amount'))['total'] or 0
        return payments_sum >= obj.amount



class UserPaymentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    transaction = CompanyTransactionSerializer(read_only=True)
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = UserPayment
        fields = [
            'id', 'user', 'transaction', 'amount',
            'payment_date', 'payment_method', 'notes', 'created_at', 'updated_at',
            'is_completed'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'user', 'transaction', 'is_completed', 'is_closed'
        ]


    def get_is_completed(self, obj):
        transaction = obj.transaction
        if transaction.split_amount:
            user_total = UserPayment.objects.filter(transaction=transaction, user=obj.user).aggregate(total=Sum('amount'))['total'] or 0
            per_user_required = transaction.amount / 6
            return user_total >= per_user_required
        else:
            payments_sum = UserPayment.objects.filter(transaction=transaction).aggregate(total=Sum('amount'))['total'] or 0
            return payments_sum >= transaction.amount


class SplitTransactionSerializer(serializers.ModelSerializer):
    person = UserShortSerializer(read_only=True)
    is_closed = serializers.SerializerMethodField()
    amount_per_partner = serializers.SerializerMethodField()
    number_of_partners = serializers.SerializerMethodField()

    class Meta:
        model = CompanyTransaction
        fields = [
            'id', 'transaction_type', 'amount', 'person', 'date_time',
            'split_amount', 'image', 'notes', 'created_at', 'updated_at', 
            'is_closed', 'amount_per_partner', 'number_of_partners'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'person', 'is_closed', 'amount_per_partner', 'number_of_partners']

    def get_is_closed(self, obj):
        payments_sum = UserPayment.objects.filter(transaction=obj).aggregate(total=Sum('amount'))['total'] or 0
        return payments_sum >= obj.amount

    def get_number_of_partners(self, obj):
        return User.objects.filter(user_type='partner').count()

    def get_amount_per_partner(self, obj):
        number_of_partners = self.get_number_of_partners(obj)
        if number_of_partners > 0:
            return round(obj.amount / number_of_partners, 2)
        return 0

 

