from rest_framework import serializers
from .models import Client, CompanyTransaction, Service, ServiceTransaction, Todo, UserPayment
from django.contrib.auth import get_user_model
from django.db.models import Sum



User = get_user_model()



class UserShortSerializer(serializers.ModelSerializer):
    person_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'person_name']

    def get_person_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else obj.email



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
            'total_split_amount', 'total_received_amount', 'remaining_amount','admin_status'
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

 

# Serializer for Todo model
class TodoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Todo
        fields = ['id', 'title', 'description', 'status', 'due_date', 'priority', 'status','category', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClientSerializer(serializers.ModelSerializer):
    income = serializers.SerializerMethodField()
    profit = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone', 'address', 'company_name', 'status', 'income', 'profit', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'income', 'profit']
    
    def get_income(self, obj):
        from django.db.models import Sum
        services = obj.services.all()
        total_income = ServiceTransaction.objects.filter(
            service__in=services,
            transaction_type='income'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return float(total_income)
    
    def get_profit(self, obj):
        from django.db.models import Sum
        
        services = obj.services.all()
        total_income = ServiceTransaction.objects.filter(
            service__in=services,
            transaction_type='income'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate total expense
        total_expense = ServiceTransaction.objects.filter(
            service__in=services,
            transaction_type='expense'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        profit = float(total_income) - float(total_expense)
        return profit



class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            'id',
            'client',
            'service_name',
            'description',
            'start_date',
            'end_date',
            'is_active',
            'amount',
            'is_closed',
            'created_at',
            'updated_at',
        
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class ServiceTransactionSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.service_name', read_only=True)
    client_name = serializers.CharField(source='service.client.name', read_only=True)
    added_by = UserShortSerializer(read_only=True)

    class Meta:
        model = ServiceTransaction
        fields = [
            'id',
            'service',
            'amount',
            'status',
            'notes',
            'transaction_date',
            'created_at',
            'updated_at',
            'transaction_type',
            'service_name',
            'client_name',
            'added_by',
            'image',
        ]
        read_only_fields = ['id', 'transaction_date', 'created_at', 'updated_at', 'service_name', 'client_name', 'added_by']

