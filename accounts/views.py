from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from rest_framework.generics import ListAPIView
from datetime import datetime
from .models import Client, CompanyTransaction, Service, ServiceTransaction, Todo, UserPayment
from .serializers import ClientSerializer, CompanyTransactionForPartnerSerializer, CompanyTransactionSerializer, ServiceSerializer, ServiceTransactionSerializer, TodoSerializer, UserPaymentSerializer, SplitTransactionSerializer
from django.contrib.auth import get_user_model
from rest_framework.pagination import PageNumberPagination

from rest_framework_simplejwt.tokens import RefreshToken
from authentication.serializers import ProfileSerializer

User = get_user_model()


class CompanyTransactionListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        identifier = request.data.get('email') or request.data.get('phone_number')
        password = request.data.get('password')

        if not identifier or not password:
            return Response(
                {'error': 'Email/Phone and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Try to find user by email or phone
        user = None
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if re.match(email_pattern, identifier):
            from django.contrib.auth import authenticate
            user = authenticate(username=identifier, password=password)
        else:
            try:
                user_obj = User.objects.get(phone_number=identifier)
                if user_obj.check_password(password):
                    user = user_obj
            except User.DoesNotExist:
                pass

        if user is None or not user.user_type == 'partner' and not user.user_type == 'admin':
            return Response(
                {'error': 'Invalid credentials.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:

            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': ProfileSerializer(user).data,
                'is_admin':True if user.is_superuser else False
            }, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {'error': 'Token generation failed but credentials are valid.'},
                status=status.HTTP_200_OK
            )



class PartnerListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        partners = User.objects.filter(user_type='partner')
        data = []
        from accounts.models import CompanyTransaction, UserPayment

        total_transaction_amount = 0
        total_transaction_count = 0
        partner_stats = {}

        for partner in partners:
            full_name = f"{getattr(partner, 'first_name', '')} {getattr(partner, 'last_name', '')}".strip()
            partner_data = {
                'id': partner.id,
                'name': full_name,
                'email': getattr(partner, 'email', ''),
            }

            # Calculate partner transactions (as CompanyTransaction.person)
            company_transactions = CompanyTransaction.objects.filter(person=partner, active_status=True, admin_status='approve')
            transaction_count = company_transactions.count()
            transaction_amount = company_transactions.aggregate(Sum('amount')).get('amount__sum') or 0

            partner_data['transaction_count'] = transaction_count
            partner_data['transaction_total_amount'] = float(transaction_amount)

            # Update totals for overall stats
            total_transaction_count += transaction_count
            total_transaction_amount += transaction_amount

            data.append(partner_data)

        # Transaction stats for all partners
        transaction_stats = {
            'total_transaction_count': total_transaction_count,
            'total_transaction_amount': float(total_transaction_amount)
        }

        response_payload = {
            'partners': data,
            'transaction_stats': transaction_stats
        }

        return Response(response_payload, status=status.HTTP_200_OK)


class CompanyTransactionListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        queryset = CompanyTransaction.objects.filter(active_status=True,admin_status='approve')
        month = self.request.query_params.get('month', None)
        year = self.request.query_params.get('year', None)

        if month and year:
            try:
                month = int(month)
                year = int(year)
                queryset = queryset.filter(date_time__year=year, date_time__month=month)
            except ValueError:
                pass 
        elif month:
            try:
                month = int(month)
                year = datetime.now().year
                queryset = queryset.filter(date_time__year=year, date_time__month=month)
            except ValueError:
                pass

        paginator = CompanyTransactionListPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = CompanyTransactionSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)


class SplitTransactionListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        queryset = CompanyTransaction.objects.filter(split_amount=True,admin_status='approve')
        
        # Optional filter by person
        person_id = request.query_params.get('person', None)
        # if person_id:
        #     queryset = queryset.filter(person_id=person_id)
        
        # Optional filter by is_closed status
        is_closed_param = request.query_params.get('is_closed', None)
        if is_closed_param is not None:
            from django.db.models import Sum, F, Case, When, BooleanField
            
            queryset = queryset.annotate(
                total_payments=Sum('user_payments__amount'),
                is_closed_calc=Case(
                    When(total_payments__gte=F('amount'), then=True),
                    default=False,
                    output_field=BooleanField()
                )
            )
            
            if is_closed_param.lower() == 'true':
                queryset = queryset.filter(is_closed_calc=True)
            elif is_closed_param.lower() == 'false':
                queryset = queryset.filter(is_closed_calc=False)
        
        # Pagination
        paginator = CompanyTransactionListPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)
        serializer = SplitTransactionSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)



class CompanyTransactionCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CompanyTransactionSerializer(data=request.data)
        if serializer.is_valid():
            req_status = 'new'
            if request.user.user_type == 'admin':
                req_status = 'approve'
            serializer.save(person=request.user,admin_status=req_status)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CompanyTransactionRetrieveUpdateDestroyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(CompanyTransaction, pk=pk)

    def get(self, request, pk):
        obj = self.get_object(pk)
        serializer = CompanyTransactionSerializer(obj)
        return Response(serializer.data)

    def patch(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk)
        data = request.data.copy()

        serializer = CompanyTransactionSerializer(obj, data=data, partial=True)
        if serializer.is_valid():
            serializer.save(person=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TransactionRequestsListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        queryset = CompanyTransaction.objects.filter(admin_status='new')
        
        transaction_type = request.GET.get("transaction_type")
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        
        month = request.GET.get("month")
        year = request.GET.get("year")
        if month and year:
            try:
                month = int(month)
                year = int(year)
                queryset = queryset.filter(date_time__year=year, date_time__month=month)
            except ValueError:
                pass

        serializer = CompanyTransactionSerializer(queryset.order_by('-date_time'), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class MyTransactionRequestsListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        queryset = CompanyTransaction.objects.filter(admin_status='new',person=request.user)
        
        transaction_type = request.GET.get("transaction_type")
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        
        month = request.GET.get("month")
        year = request.GET.get("year")
        if month and year:
            try:
                month = int(month)
                year = int(year)
                queryset = queryset.filter(date_time__year=year, date_time__month=month)
            except ValueError:
                pass

        serializer = CompanyTransactionSerializer(queryset.order_by('-date_time'), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ApproveTransactionAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, pk, *args, **kwargs):
        obj = get_object_or_404(CompanyTransaction, pk=pk)
        admin_status = request.data.get('admin_status')

        if admin_status not in ['approve', 'reject']:
            return Response(
                {"detail": "Invalid admin_status. Allowed: 'approve', 'reject'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        obj.admin_status = admin_status
        obj.save(update_fields=['admin_status'])
        serializer = CompanyTransactionSerializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)




## User payments
class UserPaymentCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        transaction_id = request.GET.get('transaction')

        if not transaction_id:
            return Response(
                {"detail": "'transaction' parameters are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            transaction = CompanyTransaction.objects.get(id=transaction_id)
        except CompanyTransaction.DoesNotExist:
            return Response(
                {"detail": f"CompanyTransaction with id '{transaction_id}' does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data.copy()
        serializer = UserPaymentSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user, transaction=transaction)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PersonalTransactions(APIView):
    permission_classes = [IsAuthenticated]
 
    def get(self, request, pk, *args, **kwargs):
        user_payments = UserPayment.objects.filter(transaction_id=pk)
        serializer = UserPaymentSerializer(user_payments, many=True)

        try:
            transaction = CompanyTransaction.objects.get(pk=pk)
            transaction_details = CompanyTransactionSerializer(transaction).data
        except CompanyTransaction.DoesNotExist:
            transaction_details = None

        return Response({
            'data': serializer.data,
            'details': transaction_details
        })


class PartnerTransactionsInnerPage(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, partner, transaction, *args, **kwargs):
        user_payments = UserPayment.objects.filter(user__id=partner, transaction__id=transaction)
        serializer = UserPaymentSerializer(user_payments, many=True)
        return Response(serializer.data)


class UserPaymentRetrieveUpdateDestroyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        return get_object_or_404(UserPayment, pk=pk)

    def get(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk, request.user)
        serializer = UserPaymentSerializer(obj)
        return Response(serializer.data)

    def patch(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk, request.user)
        serializer = UserPaymentSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk, request.user)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)




class PartnerTransactionsListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        partner_id = request.query_params.get('partner')
        if not partner_id:
            return Response({'error': 'Missing partner parameter.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            partner = User.objects.get(id=partner_id,user_type='partner')
        except User.DoesNotExist:
            return Response({'error': 'Partner does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        transactions = UserPayment.objects.filter(user=partner).order_by('-id')
        serializer = UserPaymentSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



## Todo 

# List and Create Todos
class TodoListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        todos = Todo.objects.all().order_by('-created_at')
        serializer = TodoSerializer(todos, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = TodoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Retrieve, Update, Delete Individual Todo
class TodoRetrieveUpdateDestroyAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get_object(self, pk):
        return get_object_or_404(Todo, pk=pk)

    def get(self, request, pk, *args, **kwargs):
        todo = self.get_object(pk)
        serializer = TodoSerializer(todo)
        return Response(serializer.data)

    def patch(self, request, pk, *args, **kwargs):
        todo = self.get_object(pk)
        serializer = TodoSerializer(todo, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, *args, **kwargs):
        todo = self.get_object(pk)
        todo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


### Client Management


# List and Create Clients
class ClientListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        clients = Client.objects.all().order_by('-created_at')
        serializer = ClientSerializer(clients, many=True)
        
        # Calculate statistics
        total_clients = clients.count()
        active_clients = clients.filter(status='active').count() if clients.filter(status__isnull=False).exists() else 0
        inactive_clients = clients.filter(status='inactive').count() if clients.filter(status__isnull=False).exists() else 0
        
        return Response({
            'clients': serializer.data,
            'statistics': {
                'total': total_clients,
                'active': active_clients,
                'inactive': inactive_clients
            }
        })

    def post(self, request, *args, **kwargs):
        serializer = ClientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Retrieve, Update, Delete Individual Client
class ClientRetrieveUpdateDestroyAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get_object(self, pk):
        return get_object_or_404(Client, pk=pk)

    def get(self, request, pk, *args, **kwargs):
        client = self.get_object(pk)
        serializer = ClientSerializer(client)
        return Response(serializer.data)

    def patch(self, request, pk, *args, **kwargs):
        client = self.get_object(pk)
        serializer = ClientSerializer(client, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, *args, **kwargs):
        client = self.get_object(pk)
        client.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


## service crud

# List and Create Services
class ServiceListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        services = Service.objects.all().order_by('-start_date')
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = ServiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Retrieve, Update, Delete Individual Service
class ServiceRetrieveUpdateDestroyAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get_object(self, pk):
        return get_object_or_404(Service, pk=pk)

    def get(self, request, pk, *args, **kwargs):
        service = self.get_object(pk)
        serializer = ServiceSerializer(service)
        return Response(serializer.data)

    def patch(self, request, pk, *args, **kwargs):
        service = self.get_object(pk)
        serializer = ServiceSerializer(service, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, *args, **kwargs):
        service = self.get_object(pk)
        service.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


## transaction billing
# ServiceTransaction List, Create
class ServiceTransactionListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        queryset = ServiceTransaction.objects.all().order_by('-transaction_date')
        service_id = request.GET.get('service')
        if service_id:
            queryset = queryset.filter(service_id=service_id)
        serializer = ServiceTransactionSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = ServiceTransactionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(added_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ServiceTransaction Retrieve, Update, Delete
class ServiceTransactionRetrieveUpdateDestroyAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get_object(self, pk):
        return get_object_or_404(ServiceTransaction, pk=pk)

    def get(self, request, pk, *args, **kwargs):
        transaction = self.get_object(pk)
        serializer = ServiceTransactionSerializer(transaction)
        return Response(serializer.data)

    def patch(self, request, pk, *args, **kwargs):
        transaction = self.get_object(pk)
        serializer = ServiceTransactionSerializer(transaction, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, *args, **kwargs):
        transaction = self.get_object(pk)
        transaction.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ServiceTransaction by Client
class ServiceTransactionsByClientAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, client_id, *args, **kwargs):
        client = get_object_or_404(Client, pk=client_id)
        services = Service.objects.filter(client=client)
        transactions = ServiceTransaction.objects.filter(
            service__in=services
        ).order_by('-transaction_date')
        
        # Optional filters
        transaction_type = request.GET.get('transaction_type')
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        
        status_filter = request.GET.get('status')
        if status_filter:
            transactions = transactions.filter(status=status_filter)
        
        serializer = ServiceTransactionSerializer(transactions, many=True)
        
        # Calculate summary
        total_income = transactions.filter(transaction_type='income').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        total_expense = transactions.filter(transaction_type='expense').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        return Response({
            'client': {
                'id': client.id,
                'name': client.name,
                'email': client.email
            },
            'summary': {
                'total_transactions': transactions.count(),
                'total_income': float(total_income),
                'total_expense': float(total_expense),
                'net_profit': float(total_income - total_expense)
            },
            'transactions': serializer.data
        }, status=status.HTTP_200_OK)


# ServiceTransaction by Service
class ServiceTransactionsByServiceAPIView(APIView):
    permission_classes = [IsAuthenticated]
    """
    Get all transactions for a specific service.
    """
    def get(self, request, service_id, *args, **kwargs):
        # Verify service exists
        service = get_object_or_404(Service, pk=service_id)
        
        # Get all transactions for this service
        transactions = ServiceTransaction.objects.filter(
            service=service
        ).order_by('-transaction_date')
        
        # Optional filters
        transaction_type = request.GET.get('transaction_type')
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        
        status_filter = request.GET.get('status')
        if status_filter:
            transactions = transactions.filter(status=status_filter)
        
        serializer = ServiceTransactionSerializer(transactions, many=True)
        
        # Calculate summary
        total_income = transactions.filter(transaction_type='income').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        total_expense = transactions.filter(transaction_type='expense').aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        return Response({
            'service': {
                'id': service.id,
                'service_name': service.service_name,
                'client_name': service.client.name,
                'amount': float(service.amount),
                'is_active': service.is_active,
                'is_closed': service.is_closed
            },
            'summary': {
                'total_transactions': transactions.count(),
                'total_income': float(total_income),
                'total_expense': float(total_expense),
                'net_profit': float(total_income - total_expense)
            },
            'transactions': serializer.data
        }, status=status.HTTP_200_OK)

