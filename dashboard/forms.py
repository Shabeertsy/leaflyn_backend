from django import forms
from user.models import Categories, Colors, Coupon, Product, ProductVariant, Sizes, CareGuide, ServiceCategory, Service, ServiceFeature, ServiceImage




class CategoriesForm(forms.ModelForm):
    class Meta:
        model = Categories
        fields = ['category_name', 'icon']


class SizeForm(forms.ModelForm):
    class Meta:
        model = Sizes
        fields = ['size', 'measurement']


class ProductColorForm(forms.ModelForm):
    class Meta:
        model = Colors
        fields = ['name','color']


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields='__all__'


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = [
            'product', 
            'color', 
            'size', 
            'stock', 
            'price', 
            'variant',
            'offer_type', 
            'description',
            'offer',
            'height',
            'pot_size',
            'light',
            'water',
            'growth_rate',
            'is_bestseller',
            'is_featured_collection'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['color'].required = False
        self.fields['size'].required = False
        self.fields['variant'].required = False
        self.fields['offer_type'].required = False
        self.fields['height'].required = False
        self.fields['pot_size'].required = False
        self.fields['light'].required = False
        self.fields['water'].required = False
        self.fields['growth_rate'].required = False
        self.fields['is_bestseller'].required = False
        self.fields['is_featured_collection'].required = False


class CareGuideForm(forms.ModelForm):
    class Meta:
        model = CareGuide
        fields = ['title', 'content', 'is_active', 'order']


class CouponForm(forms.ModelForm):

    class Meta:
        model = Coupon
        fields='__all__'


class ServiceCategoryForm(forms.ModelForm):
    class Meta:
        model = ServiceCategory
        fields = ['name', 'icon']


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['category', 'name', 'price', 'image']


class ServiceFeatureForm(forms.ModelForm):
    class Meta:
        model = ServiceFeature
        fields = ['name']


class ServiceImageForm(forms.ModelForm):
    class Meta:
        model = ServiceImage
        fields = ['image', 'order_by']


# payment/forms.py
from django import forms
from payment.models import PaymentGateway
import json
from django.core.exceptions import ValidationError


class PaymentGatewayForm(forms.ModelForm):
    class Meta:
        model = PaymentGateway
        fields = [
            'name',
            'display_name',
            'is_active',
            'is_default',
            'environment',
            'credentials',
            'configuration',
            'priority',
            'logo',
            'description',
            'supports_refund',
            'supports_recurring',
            'supports_upi',
            'supports_cards',
            'supports_netbanking',
            'supports_wallets',
            'min_amount',
            'max_amount',
            'transaction_fee_percentage',
            'transaction_fee_fixed',
        ]

        widgets = {
            'credentials': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': '{"api_key": "YOUR_KEY", "secret": "YOUR_SECRET"}',
                'class': 'form-control'
            }),
            'configuration': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': '{"webhook_url": "https://..."}',
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'min_amount': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'max_amount': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'transaction_fee_percentage': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'transaction_fee_fixed': forms.NumberInput(attrs={'step': '0.01', 'class': 'form-control'}),
            'priority': forms.NumberInput(attrs={'min': 0, 'max': 255, 'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control-file'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make fields optional as per your logic
        optional = [
            'logo', 'priority', 'description', 'max_amount',
            'supports_recurring', 'supports_upi', 'supports_wallets',
            'configuration', 'is_active', 'is_default',
            'transaction_fee_percentage', 'transaction_fee_fixed'
        ]
        for field in optional:
            self.fields[field].required = False

        # Required fields
        self.fields['name'].required = True
        self.fields['display_name'].required = True
        self.fields['credentials'].required = True
        self.fields['min_amount'].required = True

        # Set default values
        self.fields['is_active'].initial = True
        self.fields['is_default'].initial = False
        self.fields['environment'].initial = 'sandbox'
        self.fields['min_amount'].initial = '1.00'

        # Add CSS classes to all fields
        for field_name, field in self.fields.items():
            if field_name not in ['credentials', 'configuration', 'description', 'logo']:
                if not field.widget.attrs.get('class'):
                    field.widget.attrs['class'] = 'form-control'

    # JSON Validation
    def clean_credentials(self):
        data = self.cleaned_data.get('credentials', '{}')
        if isinstance(data, dict):
            return data
        try:
            parsed = json.loads(data)
            if not isinstance(parsed, dict):
                raise ValidationError('Credentials must be a JSON object.')
            return parsed
        except json.JSONDecodeError:
            raise ValidationError('Invalid JSON in credentials.')

    def clean_configuration(self):
        data = self.cleaned_data.get('configuration')
        if not data:
            return {}
        if isinstance(data, dict):
            return data
        try:
            parsed = json.loads(data)
            if not isinstance(parsed, dict):
                raise ValidationError('Configuration must be a JSON object.')
            return parsed
        except json.JSONDecodeError:
            raise ValidationError('Invalid JSON in configuration.')