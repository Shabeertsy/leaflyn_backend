from django.contrib import admin

# Register your models here.

from .models import UserPayment,CompanyTransaction

admin.site.register(UserPayment)
admin.site.register(CompanyTransaction)
