from django.utils import timezone
from decimal import ROUND_HALF_UP, Decimal
from django.db import models
from authentication.models import Profile, BaseModel
import uuid


class CompanyContact(BaseModel):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='company_contact',null=True,blank=True)
    company_name = models.CharField(max_length=255, verbose_name="Company Name")
    company_email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="Company Email")
    company_phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Company Phone")
    company_website = models.CharField(max_length=255, blank=True, null=True, verbose_name="Company Website")
    company_address = models.TextField(blank=True, null=True, verbose_name="Company Address")
    company_city = models.CharField(max_length=255, blank=True, null=True, verbose_name="Company City")
    company_state = models.CharField(max_length=255, blank=True, null=True, verbose_name="Company State")
    company_zip = models.CharField(max_length=20, blank=True, null=True, verbose_name="Company Zip")
    instagram = models.CharField(max_length=255, blank=True, null=True, verbose_name="Instagram")
    facebook = models.CharField(max_length=255, blank=True, null=True, verbose_name="Facebook")
    twitter = models.CharField(max_length=255, blank=True, null=True, verbose_name="Twitter")
    linkedin = models.CharField(max_length=255, blank=True, null=True, verbose_name="LinkedIn") 
    youtube = models.CharField(max_length=255, blank=True, null=True, verbose_name="Youtube")
    tiktok = models.CharField(max_length=255, blank=True, null=True, verbose_name="Tiktok")
    whatsapp = models.CharField(max_length=255, blank=True, null=True, verbose_name="Whatsapp")
    telegram = models.CharField(max_length=255, blank=True, null=True, verbose_name="Telegram")
    

    class Meta:
        verbose_name = "Company Contact"
        verbose_name_plural = "Company Contacts"

    def __str__(self):
        return f"{self.company_name}"



class ShippingAddress(BaseModel):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='shipping_addresses', db_index=True, verbose_name="User")
    address_line_1 = models.CharField(max_length=255, verbose_name="Address Line 1")
    address_line_2 = models.CharField(max_length=255, blank=True,null=True, verbose_name="Address Line 2")
    building_name_or_number = models.CharField(max_length=255, blank=True,null=True, verbose_name="Building Name or Number")
    place=models.CharField(max_length=255, blank=True,null=True, verbose_name="Place")
    district=models.CharField(max_length=255, blank=True,null=True, verbose_name="District")
    city = models.CharField(max_length=100, db_index=True, verbose_name="City")
    state = models.CharField(max_length=100, db_index=True, verbose_name="State")
    pin_code = models.CharField(max_length=20, db_index=True, verbose_name="Postal Code")
    country = models.CharField(max_length=100, db_index=True, verbose_name="Country")
    phone_number = models.CharField(max_length=15, blank=True, verbose_name="Phone Number")
    address_type = models.CharField(max_length=10, choices=[('home', 'Home'), ('office', 'Office'), ('other', 'Other')], default='home', verbose_name="Address Type")
    is_default = models.BooleanField(default=False, verbose_name="Is Default")

    class Meta:
        indexes = [
            models.Index(fields=['user', 'city']),
            models.Index(fields=['pin_code', 'country']),
        ]
        verbose_name = "Shipping Address"
        verbose_name_plural = "Shipping Addresses"

    def __str__(self):
        return f"{self.user.email} - {self.address_line_1}, {self.city}"


class Categories(BaseModel):
    category_name = models.CharField(max_length=255, db_index=True, verbose_name="Category Name")
    icon = models.ImageField(upload_to='category_icons/', blank=True, null=True, verbose_name="Category Icon")
    
    class Meta:
        indexes = [
            models.Index(fields=['category_name']),
        ]
        verbose_name = "Category"
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.category_name


class Colors(BaseModel):
    name = models.CharField(max_length=100, null=True, blank=True, db_index=True, verbose_name="Color Name")
    color = models.CharField(max_length=255, db_index=True, verbose_name="Color Code")
    
    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['color']),
        ]
        verbose_name = "Color"
        verbose_name_plural = "Colors"
    
    def __str__(self):
        return self.name


class Sizes(BaseModel):
    size = models.CharField(max_length=100, db_index=True, verbose_name="Size")
    measurement = models.CharField(max_length=50, blank=True, null=True, verbose_name="Measurement")
    
    class Meta:
        indexes = [
            models.Index(fields=['size']),
        ]
        verbose_name = "Size"
        verbose_name_plural = "Sizes"
    
    def __str__(self):
        return self.size


class Product(BaseModel):
    category = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name='products', db_index=True, verbose_name="Category")
    name = models.CharField(max_length=255, db_index=True, verbose_name="Product Name")
    title = models.CharField(max_length=255, blank=True, null=True, db_index=True, verbose_name="Product Title")
    base_price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True, verbose_name="Base Price",null=True,blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['category', 'name']),
            models.Index(fields=['base_price']),
        ]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.name


class ProductVariant(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants', db_index=True, verbose_name="Product")
    color = models.ForeignKey(Colors, on_delete=models.CASCADE, related_name='variant_color', null=True, blank=True, db_index=True, verbose_name="Color")
    size = models.ForeignKey(Sizes, on_delete=models.CASCADE, related_name='variant_sizes', null=True, blank=True, db_index=True, verbose_name="Size")
    stock = models.PositiveIntegerField(db_index=True, verbose_name="Stock Quantity")
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True, verbose_name="Price")
    variant =  models.CharField(max_length=255, null=True,blank=True)
    offer_type = models.CharField(max_length=255, null=True, choices=[('percentage', 'Percentage'), ('amount', 'Amount')], db_index=True, verbose_name="Offer Type")
    offer = models.FloatField(default=0.0, db_index=True, verbose_name="Offer Value")
    description = models.TextField(blank=True, verbose_name="Description")
    height = models.CharField(max_length=100, blank=True, null=True, verbose_name="Height")
    pot_size = models.CharField(max_length=100, blank=True, null=True, verbose_name="Pot Size")
    light = models.CharField(max_length=100, blank=True, null=True, verbose_name="Light")
    water = models.CharField(max_length=100, blank=True, null=True, verbose_name="Water")
    growth_rate = models.CharField(max_length=100, blank=True, null=True, verbose_name="Growth Rate")
    is_featured_collection = models.BooleanField(default=False, db_index=True, verbose_name="Is Featured Collection")
    is_bestseller = models.BooleanField(default=False, db_index=True, verbose_name="Is Bestseller")

    class Meta:
        indexes = [
            models.Index(fields=['product', 'color', 'size']),
            models.Index(fields=['stock']),
            models.Index(fields=['price']),
            models.Index(fields=['offer_type', 'offer']),
        ]
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"

    def discounted_price(self):
        price = self.price if self.price is not None else Decimal('0.00')
        offer = Decimal(str(self.offer)) if self.offer is not None else Decimal('0.00')

        if self.offer_type == 'percentage':
            discount = price * (Decimal('1.0') - (offer / Decimal('100')))
            return discount.quantize(Decimal('0.01'))
        elif self.offer_type == 'amount':
            discounted = price - offer
            return max(discounted, Decimal('0.00')).quantize(Decimal('0.01'))
        return price.quantize(Decimal('0.01'))

    def __str__(self):
        return f"{self.product.name} -   {self.size or ''}".strip()


class CareGuide(BaseModel):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='care_guides', db_index=True, verbose_name="Product Variant")
    title = models.CharField(max_length=255, verbose_name="Care Guide Title", default="General Care")
    content = models.TextField(blank=True, null=True, verbose_name="Content")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    order = models.PositiveIntegerField(default=0, verbose_name="Display Order")
    

    class Meta:
        verbose_name = "Care Guide"
        verbose_name_plural = "Care Guides"
        ordering = ['order', '-created_at']
        indexes = [
            models.Index(fields=['variant', 'is_active']),
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return f"{self.title} - {self.variant.product.name}"


class ProductImage(BaseModel):
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='images', db_index=True, verbose_name="Product Variant")
    image = models.ImageField(upload_to='product_images/', verbose_name="Image")
    order_by = models.IntegerField(default=1, db_index=True, verbose_name="Display Order")

    class Meta:
        indexes = [
            models.Index(fields=['variant', 'order_by']),
        ]
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"

    def __str__(self):
        return f"Image for {self.variant}"


class ServiceCategory(BaseModel):
    name = models.CharField(max_length=255, db_index=True, verbose_name="Service Category Name")
    icon = models.ImageField(upload_to='service_category_icons/', blank=True, null=True, verbose_name="Service Category Icon")
    
    class Meta:
        indexes = [
            models.Index(fields=['name']),
        ]
        verbose_name = "Service Category"
        verbose_name_plural = "Service Categories"
    
    def __str__(self):
        return self.name


class Service(BaseModel):
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='services', db_index=True, verbose_name="Service Category")
    name = models.CharField(max_length=255, db_index=True, verbose_name="Service Name")
    description = models.TextField(blank=True, null=True, verbose_name="Service Description")
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True, verbose_name="Service Price",default=0)
    image = models.ImageField(upload_to='service_images/', blank=True, null=True, verbose_name="Service Image")
    
    class Meta:
        indexes = [
            models.Index(fields=['category', 'name']),
            models.Index(fields=['price']),
        ]
        verbose_name = "Service"
        verbose_name_plural = "Services"
    
    def __str__(self):
        return self.name

class ServiceFeature(BaseModel):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='features', db_index=True, verbose_name="Service")
    name = models.CharField(max_length=255, db_index=True, verbose_name="Feature Name")
    
    class Meta:
        indexes = [
            models.Index(fields=['service', 'name']),
        ]
        verbose_name = "Service Feature"
        verbose_name_plural = "Service Features"
    
    def __str__(self):
        return self.name


class ServiceImage(BaseModel):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='images', db_index=True, verbose_name="Service")
    image = models.ImageField(upload_to='service_images/', blank=True, null=True, verbose_name="Service Image")
    order_by = models.IntegerField(default=1, db_index=True, verbose_name="Display Order")
    
    class Meta:
        indexes = [
            models.Index(fields=['service', 'order_by']),
        ]
        verbose_name = "Service Image"
        verbose_name_plural = "Service Images"
    
    def __str__(self):
        return f"Image for {self.service.name}"


class ServiceBooking(BaseModel):
    class BookingStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='service_bookings', db_index=True, verbose_name="User")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='bookings', db_index=True, verbose_name="Service")
    booking_date = models.DateTimeField(db_index=True, verbose_name="Booking Date")
    status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.PENDING, db_index=True, verbose_name="Booking Status")
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'service', 'booking_date']),
            models.Index(fields=['status']),
        ]
        verbose_name = "Service Booking"
        verbose_name_plural = "Service Bookings"
    
    def __str__(self):
        return f"Booking for {self.service.name} by {self.user.email}"

class Cart(BaseModel):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='cart', db_index=True, verbose_name="User")
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='carts', db_index=True, verbose_name="Applied Coupon")

    class Meta:
        indexes = [
            models.Index(fields=['user']),
        ]
        verbose_name = "Shopping Cart"
        verbose_name_plural = "Shopping Carts"

    def total(self):
        total = sum(item.line_total() for item in self.items.all())
        if self.coupon:
            if self.coupon.offer_type == 'percentage':
                total -= total * (self.coupon.offer / 100)
            elif self.coupon.offer_type == 'amount':
                total -= self.coupon.offer
        return max(total, 0)

    def __str__(self):
        return f"Cart for {self.user.email}"


class CartItem(BaseModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items', db_index=True, verbose_name="Cart")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, db_index=True, verbose_name="Product Variant")
    quantity = models.PositiveIntegerField(default=1, db_index=True, verbose_name="Quantity")

    class Meta:
        unique_together = ('cart', 'variant')
        indexes = [
            models.Index(fields=['cart', 'variant']),
            models.Index(fields=['quantity']),
        ]
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"

    def line_total(self):
        return self.variant.discounted_price() * self.quantity

    def __str__(self):
        return f"{self.variant} x{self.quantity}"


class Wishlist(BaseModel):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='wishlist_items', db_index=True, verbose_name="User")
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, db_index=True, verbose_name="Product Variant")

    class Meta:
        unique_together = ('user', 'variant')
        indexes = [
            models.Index(fields=['user', 'variant']),
        ]
        verbose_name = "Wishlist Item"
        verbose_name_plural = "Wishlist Items"

    def __str__(self):
        return f"{self.user.email} - {self.variant.product.name}"


class Coupon(BaseModel):
    name = models.CharField(max_length=255, db_index=True, verbose_name="Coupon Name")
    code = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="Coupon Code")
    valid_from = models.DateTimeField(db_index=True, verbose_name="Valid From")
    valid_to = models.DateTimeField(db_index=True, verbose_name="Valid To")
    name=models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    offer_type=models.CharField(max_length=255,null=True,choices=[('percentage', 'Percentage'), ('amount', 'Amount')])
    offer = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    max_price=models.FloatField(default=0.0)
    min_price=models.FloatField(default=0.0)
    
    def __str__(self):
        return f"{self.code} - {self.offer_type}% off"



class Order(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='orders')
    shipping_address = models.ForeignKey(ShippingAddress, on_delete=models.SET_NULL, null=True, related_name='orders')

    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    coupon_offer = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    @property
    def subtotal(self):
        return sum(item.price * item.quantity for item in self.items.all())

    def __str__(self):
        return f"Order #{self.id} - {self.user.email}"

    def calculate_total(self):
        total = self.subtotal
        discount_amount = 0

        if self.coupon:
            offer_type = self.coupon.offer_type
            offer_value = Decimal(str(self.coupon.offer or 0))
            min_price = Decimal(str(self.coupon.min_price or 0))
            max_price = Decimal(str(self.coupon.max_price or 0))
            total_decimal = Decimal(str(total))

            if offer_type == 'percentage':
                discount_amount = (total_decimal * (offer_value / Decimal('100'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            elif offer_type == 'amount':
                discount_amount = offer_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                if discount_amount > total_decimal:
                    discount_amount = total_decimal
            else:
                discount_amount = Decimal('0.00')

            if total_decimal < min_price:
                discount_amount = Decimal('0.00')

            if max_price and discount_amount > max_price:
                discount_amount = max_price

            total_decimal -= discount_amount
            return total_decimal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal(str(total)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if not is_new or self.items.exists():
            new_total = self.calculate_total()
            print(new_total, 'total')
            if self.total_amount != new_total:
                self.total_amount = new_total
                Order.objects.filter(pk=self.pk).update(total_amount=new_total)


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        product_name = getattr(self.variant.product, 'name', 'Unknown Product')
        order_id = self.order.id or 'New'
        return f"{product_name} (x{self.quantity}) for Order #{order_id}"



class Notification(BaseModel):
    NOTIFICATION_TYPE_CHOICES = [
        ('order_placed', 'Order Placed'),
        ('order_confirmed', 'Order Confirmed'),
        ('order_shipped', 'Order Shipped'),
        ('order_delivered', 'Order Delivered'),
        ('order_cancelled', 'Order Cancelled'),
        ('order_returned', 'Order Returned'),
        ('payment_success', 'Payment Success'),
        ('payment_failed', 'Payment Failed'),
        ('promotion', 'Promotion'),
        ('system', 'System'),
        ('other', 'Other'),
    ]


    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    user = models.ForeignKey('authentication.Profile', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=True, null=True, related_name='notifications')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at =timezone.now()
            self.save()

    @classmethod
    def create_notification(cls, user, title, message, notification_type, priority='medium', order=None, payment=None):
        return cls.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            order=order,
            payment=payment
        )
