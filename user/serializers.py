from rest_framework import serializers
from .models import Product, ProductVariant, CareGuide, Categories
from .models import ProductImage


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Categories
        fields = [
            'uuid',
            'category_name',
            'icon',
            'created_at',
            'updated_at',
        ]
        depth = 1   


class CareGuideSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareGuide
        fields = [
            'uuid',
            'variant',
            'title',
            'content',
            'is_active',
            'order',
            'created_at',
            'updated_at',
        ]
        depth = 1

class ProductVariantImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = [
            'uuid',
            'image',
            'created_at',
            'updated_at',
        ]


class ProductVariantSerializer(serializers.ModelSerializer):
    care_guides = CareGuideSerializer(many=True, read_only=True)
    images = ProductVariantImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProductVariant
        fields = [
            'uuid',
            'product',
            'color',
            'size',
            'stock',
            'price',
            'variant',
            'offer_type',
            'offer',
            'height',
            'pot_size',
            'light',
            'water',
            'growth_rate',
            'care_guides',
            'images',  
            'created_at',
            'updated_at',
        ]

        depth = 1

