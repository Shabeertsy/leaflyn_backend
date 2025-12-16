from django.contrib import admin

# Register your models here.

from .models import UserPayment

admin.site.register(UserPayment)
