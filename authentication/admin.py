from django.contrib import admin
from .models import Profile, OTP


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['email', 'phone_number', 'first_name', 'last_name', 'is_verified', 'user_type', 'created_at']
    list_filter = ['is_verified', 'user_type', 'is_active']
    search_fields = ['email', 'phone_number', 'first_name', 'last_name']


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ['contact', 'contact_type', 'otp_code', 'is_verified', 'expires_at', 'created_at']
    list_filter = ['contact_type', 'is_verified', 'created_at']
    search_fields = ['contact', 'otp_code']
    readonly_fields = ['created_at', 'updated_at']
