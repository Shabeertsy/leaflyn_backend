from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.pagination import PageNumberPagination
from .models import Product, ProductVariant, CareGuide, Categories
from .serializers import *


class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategoryListAPIView(APIView):
    def get(self, request): 
        try:
            categories = Categories.objects.all()
            serializer = CategorySerializer(categories, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)




class ProductListAPIView(APIView):
    def get(self, request):
        try:
            products = ProductVariant.objects.filter()

            sizes = request.query_params.getlist('size')
            colors = request.query_params.getlist('color')
            category_id = request.query_params.get('category_id')

            if sizes:
                products = products.filter(size__in=sizes)
            if colors:
                products = products.filter(color__in=colors)
            if category_id:
                products = products.filter(product__category_id=category_id)

            if not products.exists():
                return Response({"error": "No products found"}, status=status.HTTP_404_NOT_FOUND)

            # Apply pagination
            paginator = CustomPageNumberPagination()
            paginated_products = paginator.paginate_queryset(products, request)
            
            if paginated_products is not None:
                serializer = ProductVariantSerializer(paginated_products, many=True)
                return paginator.get_paginated_response(serializer.data)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ProductVariantSerializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductSingleAPIView(APIView):
    def get(self, request):
        try:
            uuids = request.query_params.getlist('uuid')
            if not uuids:
                return Response({"error": "No uuid(s) provided"}, status=status.HTTP_400_BAD_REQUEST)

            product_variants = ProductVariant.objects.filter(uuid__in=uuids)
            if not product_variants.exists():
                return Response({"error": "Product(s) not found"}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = ProductVariantSerializer(product_variants, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
