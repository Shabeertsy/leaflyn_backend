from rest_framework import serializers
from .models import Product, ProductVariant, CareGuide, Categories


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Categories
        fields = [
            'uuid',
            'category_name',
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


class ProductVariantSerializer(serializers.ModelSerializer):
    care_guides = CareGuideSerializer(many=True, read_only=True)
    
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
            'created_at',
            'updated_at',
        ]

        depth = 1

