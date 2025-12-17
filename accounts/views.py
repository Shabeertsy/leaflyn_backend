from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework.generics import ListAPIView
from datetime import datetime
from .models import CompanyTransaction, UserPayment
from .serializers import CompanyTransactionSerializer, UserPaymentSerializer
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




class CompanyTransactionCreateAPIView(APIView):

    def post(self, request, *args, **kwargs):
        serializer = CompanyTransactionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(person=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CompanyTransactionRetrieveUpdateDestroyAPIView(APIView):

    def get_object(self, pk):
        return get_object_or_404(CompanyTransaction, pk=pk)

    def get(self, request, pk):
        obj = self.get_object(pk)
        serializer = CompanyTransactionSerializer(obj)
        return Response(serializer.data)

    def put(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk)
        serializer = CompanyTransactionSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk)
        serializer = CompanyTransactionSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class PersonalTransactionListCreateAPIView(APIView):

    def post(self, request, *args, **kwargs):
        serializer = UserPaymentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
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



class PersonalTransactionRetrieveUpdateDestroyAPIView(APIView):

    def get_object(self, pk, user):
        return get_object_or_404(UserPayment, pk=pk, user=user)

    def get(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk, request.user)
        serializer = UserPaymentSerializer(obj)
        return Response(serializer.data)

    def put(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk, request.user)
        serializer = UserPaymentSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk, request.user)
        serializer = UserPaymentSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, *args, **kwargs):
        obj = self.get_object(pk, request.user)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

