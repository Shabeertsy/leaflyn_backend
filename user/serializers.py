from rest_framework import serializers
from .models import Order, OrderItem, Product, ProductVariant, CareGuide, Categories
from .models import ProductImage
from .models import CompanyContact
from dashboard.models import ContactUs, CustomAd  ,TermsCondition
from decimal import Decimal
from .models import ShippingAddress,ServiceCategory,Service,ServiceFeature,ServiceImage, Cart, CartItem, Wishlist



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

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingAddress
        fields = [
            'uuid',
            'address_line_1',
            'address_line_2',
            'building_name_or_number',
            'place',
            'district',
            'city',
            'state',
            'pin_code',
            'country',
            'phone_number',
            'address_type',
            'is_default',
            'created_at',
            'updated_at',
        ]

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
            'description',
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
        return max(Decimal('0.00'), calculated_price).quantize(Decimal('0.1'))


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


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = [
            'uuid',
            'id',
            'name',
            'icon',
            'created_at',
            'updated_at',
        ]
        depth = 1


class ServiceFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceFeature
        fields = [
            'uuid',
            'id',
            'name',
        ]


class ServiceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceImage
        fields = [
            'uuid',
            'id',
            'image',
            'order_by',
        ]


class ServiceSerializer(serializers.ModelSerializer):
    features = ServiceFeatureSerializer(many=True, read_only=True)
    images = ServiceImageSerializer(many=True, read_only=True)

    class Meta:
        model = Service
        fields = [
            'uuid',
            'id',
            'category',
            'name',
            'description',
            'price',
            'image',
            'features',
            'images',
            'created_at',
            'updated_at',
        ]
        depth = 1


class CustomAdSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomAd
        fields = [
            'id',
            'title',
            'image',
            'target_url',
            'ad_type',
            'start_date',
            'end_date',
            'priority',
            'is_active',
            'created_at',
            'description'
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CartItemSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            'uuid',
            'variant',
            'quantity',
            'line_total',
            'created_at',
            'updated_at',
        ]

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            'uuid',
            'items',
            'total',
            'created_at',
            'updated_at',
        ]

    def get_total(self, obj):
        return obj.total()


class WishlistSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = [
            'uuid',
            'variant',
            'created_at',
            'updated_at',
        ]

class OrderItemSerializer(serializers.ModelSerializer):
    product_variant = ProductVariantSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product_variant',
            'quantity',
            'price',
            'created_at',
            'updated_at'
        ]
        
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = AddressSerializer(read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    coupon = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'uuid',
            'user',
            'shipping_address',
            'status',
            'total_amount',
            'coupon',
            'coupon_offer',
            'items',
            'created_at',
            'updated_at'
        ]
