from django.contrib import admin
from .models import Notification, Product, ProductVariant, ProductImage, Cart, CartItem, Wishlist, Coupon, Order, OrderItem, ShippingAddress, Categories, Colors, Sizes, CareGuide
# Register your models here.


admin.site.register(Product)
admin.site.register(ProductVariant)
admin.site.register(ProductImage)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Wishlist)
admin.site.register(Coupon)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(ShippingAddress)
admin.site.register(Categories)
admin.site.register(Colors)
admin.site.register(Sizes)
admin.site.register(Notification)
admin.site.register(CareGuide)



