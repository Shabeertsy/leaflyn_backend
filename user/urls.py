from django.urls import path
from . import views




urlpatterns = [
    path('product-variants/', views.ProductListAPIView.as_view(), name='product-variants'),
    path('product-details/', views.ProductSingleAPIView.as_view(), name='product-details'),


    path('categories/', views.CategoryListAPIView.as_view(), name='categories'),

    path('product-collection/', views.ProductCollectionListAPIView.as_view(), name='product-collection'),
    
]
