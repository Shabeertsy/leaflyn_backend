from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework.generics import ListAPIView
from datetime import datetime
from .models import CompanyTransaction, UserPayment
from .serializers import CompanyTransactionForPartnerSerializer, CompanyTransactionSerializer, UserPaymentSerializer, SplitTransactionSerializer
from django.contrib.auth import get_user_model
from rest_framework.pagination import PageNumberPagination


User = get_user_model()


class PartnerListAPIView(APIView):

    def get(self, request, *args, **kwargs):
        partners = User.objects.filter(is_partner=True)

        data = []
        for partner in partners:
            full_name = f"{getattr(partner, 'first_name', '')} {getattr(partner, 'last_name', '')}".strip()
            partner_data = {
                'id': partner.id,
                'name': full_name,
                'email': getattr(partner, 'email', ''),
            }
            data.append(partner_data)
        return Response(data, status=status.HTTP_200_OK)



class CompanyTransactionListPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class CompanyTransactionListAPIView(APIView):
    def get(self, request, *args, **kwargs):
        queryset = CompanyTransaction.objects.all()
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

    def get(self, request, *args, **kwargs):
        queryset = CompanyTransaction.objects.filter(split_amount=True)
        
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

    def post(self, request, *args, **kwargs):
        serializer = CompanyTransactionSerializer(data=request.data)
        person=get_object_or_404(User,id=request.data.get('person'))
        if serializer.is_valid():
            serializer.save(person=person)
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

        person_id = data.get('person', None)
        if person_id is not None:
            person = get_object_or_404(User, id=person_id)
            serializer = CompanyTransactionSerializer(obj, data=data, partial=True)
            if serializer.is_valid():
                serializer.save(person=person)
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = CompanyTransactionSerializer(obj, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



## User payments
class UserPaymentCreateAPIView(APIView):

    def post(self, request, *args, **kwargs):
        user_id = request.GET.get('user')
        transaction_id = request.GET.get('transaction')

        if not user_id or not transaction_id:
            return Response(
                {"detail": "Both 'user' and 'transaction' parameters are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": f"User with id '{user_id}' does not exist."},
                status=status.HTTP_404_NOT_FOUND
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
            serializer.save(user=user, transaction=transaction)
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
        print(user_payments,'asdfa')
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
            partner = User.objects.get(id=partner_id, is_partner=True)
        except User.DoesNotExist:
            return Response({'error': 'Partner does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        transactions = UserPayment.objects.filter(user=partner).order_by('-id')
        serializer = UserPaymentSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
