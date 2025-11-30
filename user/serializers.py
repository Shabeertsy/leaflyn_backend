from rest_framework import serializers
from .models import Product, ProductVariant, CareGuide, Categories
from .models import ProductImage
from .models import CompanyContact
from dashboard.models import ContactUs  ,TermsCondition
from decimal import Decimal


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Categories
        fields = [
            'uuid',
            'id',
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


class ContactUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUs
        fields = [
            'name',
            'email',
            'phone',
            'content',
            'subject',
        ]


class TermsConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsCondition
        fields = [
            'title',
            'content',
            'created_at',
            'updated_at',
        ]


class CompanyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyContact
        fields = [
            'uuid',
            'id',
            'company_name',
            'company_email',
            'company_phone',
            'company_address',
            'company_city',
            'company_state',
            'company_zip',
            'instagram',
            'facebook',
            'twitter',
            'linkedin',
            'youtube',
            'tiktok',
            'whatsapp',
            'telegram',
            'created_at',
            'updated_at',
        ]

class ProductVariantSerializer(serializers.ModelSerializer):
    care_guides = CareGuideSerializer(many=True, read_only=True)
    images = ProductVariantImageSerializer(many=True, read_only=True)
    price= serializers.SerializerMethodField()
    original_price= serializers.SerializerMethodField()
    offer_percentage= serializers.SerializerMethodField()    
    name= serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            'uuid',
            'product',
            'color',
            'size',
            'original_price',
            'stock',
            'price',
            'variant',
            'offer_type',
            'offer',
            'height',
            'pot_size',
            'offer_percentage',
            'light',
            'water',
            'growth_rate',
            'care_guides',
            'name',
            'images',  
            'created_at',
            'updated_at',
        ]

        depth = 1

    def get_price(self, obj):
        offer_value = Decimal(str(obj.offer)) if obj.offer is not None else Decimal('0.00')
        
        if obj.offer_type == 'amount':
            calculated_price = obj.price - offer_value
        elif obj.offer_type == 'percentage':
            percent_decimal = offer_value / Decimal('100.00')
            calculated_price = obj.price - (obj.price * percent_decimal)
        else:
            calculated_price = obj.price
        return max(Decimal('0.00'), calculated_price)


    def get_original_price(self, obj):
        return obj.price


    def get_offer_percentage(self, obj):
        offer_value = Decimal(str(obj.offer)) if obj.offer is not None else Decimal('0.00')
        product_price = obj.price if obj.price is not None else Decimal('0.00')

        if offer_value == Decimal('0.00') or product_price == Decimal('0.00'):
            return Decimal('0.00')

        if obj.offer_type == 'percentage':
            return offer_value
        elif obj.offer_type == 'amount':
            return (offer_value / product_price) * Decimal('100.00')
        else:
            return Decimal('0.00')

    def get_name(self, obj):
        return  f"{obj.product.name} {obj.variant}"