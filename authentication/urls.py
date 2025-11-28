from django.urls import path
from . import views


urlpatterns = [
    # Traditional authentication
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    
    # OTP-based authentication
    path('send-otp/', views.SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', views.VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', views.ResendOTPView.as_view(), name='resend-otp'),
]
