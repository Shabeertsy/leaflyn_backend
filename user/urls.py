from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from authentication.views import (
    SendOTPView,
    VerifyOTPView,
    ResendOTPView,
    RegisterAPIView,
    LoginView,
    PersonalInfo,
)



urlpatterns = [

    # Authentication
    # Traditional authentication
    path('register/', RegisterAPIView.as_view(), name='register_api'),
    path('login/', LoginView.as_view(), name='login_api'),
    path('refresh-token/', TokenRefreshView.as_view(), name='refresh-token_api'),

    path('personal-info/', PersonalInfo.as_view(), name='personal-info'),
        
    # OTP-based authentication
    path('send-otp/', SendOTPView.as_view(), name='send-otp_api'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),



    # Product
    path('product-variants/', views.ProductListAPIView.as_view(), name='product-variants'),
    path('product-details/', views.ProductSingleAPIView.as_view(), name='product-details'),

    path('categories/', views.CategoryListAPIView.as_view(), name='categories'),
    path('product-collection/', views.ProductCollectionListAPIView.as_view(), name='product-collection'),

    path('contact-us/', views.ContactUsAPIView.as_view(), name='contact-us-api'),
    path('terms-condition/', views.TermsConditionAPIView.as_view(), name='terms-condition-api'),
    path('company-contact/', views.CompanyContactAPIView.as_view(), name='company-contact-api'),
    
]
