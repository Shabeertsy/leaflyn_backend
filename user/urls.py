from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from authentication.views import (
    GoogleAuthView,
    SendOTPView,
    VerifyOTPView,
    ResendOTPView,
    RegisterAPIView,
    LoginView,
    PersonalInfo,
    RegisterUserAndAddressAPIView,
    GoogleAuthView,
)



urlpatterns = [

    # Authentication
    # Traditional authentication
    path('register/', RegisterAPIView.as_view(), name='register_api'),
    path('login/', LoginView.as_view(), name='login_api'),
    path('refresh-token/', TokenRefreshView.as_view(), name='refresh-token_api'),
    path('register-user-address/', RegisterUserAndAddressAPIView.as_view(), name='register-user-address'),

    path("google/", GoogleAuthView.as_view(), name="google-auth"),



    path('personal-info/', PersonalInfo.as_view(), name='personal-info'),
        
    # OTP-based authentication
    path('send-otp/', SendOTPView.as_view(), name='send-otp_api'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),


    # Address
    path('address-list/', views.ListAddressAPIView.as_view(), name='address-list'),
    path('address-add/', views.AddressAddAPIView.as_view(), name='address-add'),
    path('address-update/<str:uuid>/', views.AddressUpdateAPIView.as_view(), name='address-update'),
    path('address-delete/<str:uuid>/', views.AddressDeleteAPIView.as_view(), name='address-delete'),



    # Product
    path('product-variants/', views.ProductListAPIView.as_view(), name='product-variants'),
    path('product-details/', views.ProductSingleAPIView.as_view(), name='product-details'),

    path('similar-product/', views.SimilarProductListAPIView.as_view(), name='similar-product'),


    # Service
    path('service-category/', views.ListServiceCategoryAPIView.as_view(), name='service-category'),
    path('service-list/', views.ListServiceAPIView.as_view(), name='service-list'),

    path('categories/', views.CategoryListAPIView.as_view(), name='categories'),
    path('product-collection/', views.ProductCollectionListAPIView.as_view(), name='product-collection'),

    path('contact-us/', views.ContactUsAPIView.as_view(), name='contact-us-api'),
    path('terms-condition/', views.TermsConditionAPIView.as_view(), name='terms-condition-api'),
    path('company-contact/', views.CompanyContactAPIView.as_view(), name='company-contact-api'),

    path('custom-ads/', views.CustomAdListAPIView.as_view(), name='custom-ads-api'),
    
    # Cart
    path('cart/', views.CartAPIView.as_view(), name='cart'),
    path('add-to-cart/', views.AddToCartAPIView.as_view(), name='add-to-cart'),
    path('remove-from-cart/<str:uuid>/', views.RemoveFromCartAPIView.as_view(), name='remove-from-cart'),
    path('update-cart-item/<str:uuid>/', views.UpdateCartItemAPIView.as_view(), name='update-cart-item'),

    path('sync-cart/', views.SyncCartAPIView.as_view(), name='sync-cart'),

    # Notification 
    path('notifications/', views.NotificationListAPIView.as_view(), name='notification-list'),
    path('notifications/mark-as-read/<int:pk>/', views.NotificationMarkAsReadAPIView.as_view(), name='notification-mark-as-read'),


    path('my-orders/', views.MyOrdersAPIView.as_view(), name='my-orders'),

    path('order/cod/', views.CreateCashOnDeliveryOrderAPIView.as_view(), name='order-cod'),

    # Wishlist
    path('wishlist/', views.WishlistAPIView.as_view(), name='wishlist'),
]
