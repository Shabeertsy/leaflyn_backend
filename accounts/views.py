from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework.generics import ListAPIView
from datetime import datetime
from .models import CompanyTransaction, UserPayment
from .serializers import CompanyTransactionForPartnerSerializer, CompanyTransactionSerializer, UserPaymentSerializer
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



class CompanyTransactionForPartnersListAPIView(APIView):
    def get(self, request, *args, **kwargs):
        queryset = CompanyTransaction.objects.filter(split_amount=True,admin_status='approve').order_by('-id')
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
        serializer = CompanyTransactionForPartnerSerializer(paginated_queryset, many=True)
        return paginator.get_paginated_response(serializer.data)



class CompanyTransactionCreateAPIView(APIView):

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


class ApproveTransactionAPIView(APIView):
   
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

    def get(self, request, partner, transaction, *args, **kwargs):
        user_payments = UserPayment.objects.filter(user__id=partner, transaction__id=transaction)
        serializer = UserPaymentSerializer(user_payments, many=True)
        return Response(serializer.data)


class UserPaymentRetrieveUpdateDestroyAPIView(APIView):

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
