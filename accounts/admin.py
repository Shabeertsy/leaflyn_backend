from django.contrib import admin
from .models import Todo, Client, Service, ServiceTransaction

# Register your models here.

from .models import UserPayment,CompanyTransaction

admin.site.register(UserPayment)
admin.site.register(CompanyTransaction)

admin.site.register(Todo)
admin.site.register(Client)
admin.site.register(Service)
admin.site.register(ServiceTransaction)

