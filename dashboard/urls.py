from django.urls import path
from . import views

urlpatterns = [

    ## Main 
    path('', views.HomeView.as_view(), name='dashboard'),


    ## Authentication
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/update/', views.ProfileView.as_view(), name='profile_update'),
    path('company-contact/update/', views.ProfileView.as_view(), name='company_contact_update'),

    ## Profile
    path('notifications/', views.ViewNotifications.as_view(), name='notification_list'),
    path('notifications/mark-as-read/<int:notif_id>/', views.MarkNotificationAsReadView.as_view(), name='mark_notification_as_read'),
    path('notifications/delete/<int:notif_id>/', views.DeleteNotificationView.as_view(), name='delete_notification'),
    path('notifications/clear-all/', views.ClearAllNotificationsView.as_view(), name='clear_all_notifications'),


    ## Categories 
    path('category/', views.ProductCategoryView.as_view(), name='product_category'),
    path('category/add/', views.CategoryCreateView.as_view(), name='add_product_category'),
    path('category/edit/<int:pk>/', views.CategoryEditView.as_view(), name='category_edit'),
    path('category/delete/<int:pk>/', views.CategoryDeleteView.as_view(), name='category_delete'),
  

    ## Colors - Commented out as color functionality is being removed
    # path('colors/', views.ProductColorsView.as_view(), name='product_colors'),
    # path('colors/add/', views.ProductColorCreateView.as_view(), name='add_product_color'),
    # path('colors/edit/<int:pk>/', views.ProductColorEditView.as_view(), name='edit_product_color'),
    # path('colors/delete/<int:color_id>/', views.ProductColorDeleteView.as_view(), name='delete_product_color'),
  

    # Size 
    path('size/', views.SizesView.as_view(), name='product_size'),
    path('size/add/', views.SizeCreateView.as_view(), name='add_product_size'),
    path('size/edit/<int:pk>/', views.SizeEditView.as_view(), name='size_edit'),
    path('size/delete/<int:pk>/', views.SizeDeleteView.as_view(), name='size_delete'),
  

    ## Products 
    path('products/', views.ProductsView.as_view(), name='products'),
    path('product/add/',  views.ProductCreateView.as_view(), name='add_product'),
    path('product/edit/<int:pk>/',  views.ProductEditView.as_view(), name='edit_product'),
    path('product/delete/<int:product_id>/',  views.ProductDeleteView.as_view(), name='delete_product'),

    path('product-store/',  views.ProductStore.as_view(), name='product_store'),
  

    ## Product Variant
    path('variants/', views.ProductVariantsView.as_view(), name='product_variants'),
    path('variants/add/', views.ProductVariantCreateView.as_view(), name='add_product_variant'),
    path('variants/edit/<int:pk>/', views.ProductVariantEditView.as_view(), name='edit_product_variant'),
    path('variants/delete/<int:variant_id>/', views.ProductVariantDeleteView.as_view(), name='delete_product_variant'),
    path('delete_variant_image/<int:image_id>/', views.DeleteVariantImageView.as_view(), name='delete_variant_image'),

    # Care Guides
    path('variants/<int:variant_id>/care-guides/', views.CareGuideListView.as_view(), name='care_guide_list'),
    path('variants/<int:variant_id>/care-guides/add/', views.CareGuideCreateView.as_view(), name='add_care_guide'),
    path('care-guides/edit/<int:pk>/', views.CareGuideEditView.as_view(), name='edit_care_guide'),
    path('care-guides/delete/<int:pk>/', views.CareGuideDeleteView.as_view(), name='delete_care_guide'),
    path('care-guides/templates/', views.CareGuideTemplatesView.as_view(), name='care_guide_templates'),



    ## Offers
    path('coupon/', views.CouponListView.as_view(), name='coupon'),
    path('coupon/add/', views.CouponCreateView.as_view(), name='add_coupon'),
    path('coupon/edit/<int:pk>/', views.CouponEditView.as_view(), name='edit_coupon'),
    path('coupon/delete/<int:pk>/', views.CouponDeleteView.as_view(), name='delete_coupon'),


    ## Orders
    path('orders/', views.OrdersDashboardView.as_view(), name='orders'),
    path('download-order-excel/', views.DownloadOrdersExcelView.as_view(), name='download_order_excel'),
    path('download-order-pdf/<int:pk>/', views.DownloadOrderPDFView.as_view(), name='download_order_pdf'),
    path('orders/<int:order_id>/', views.OrderDetailView.as_view(), name='order_detail'),



    path('customers/', views.CustomersView.as_view(), name='customers'),
    path('payment/', views.PaymentView.as_view(), name='payments'),


    ## Terms and conditions
    path('terms-conditions/', views.TermsConditionListView.as_view(), name='terms_condition_list'),
    path('terms-conditions/add/', views.TermsConditionCreateView.as_view(), name='add_term_condition'),
    path('terms-conditions/edit/<int:pk>/', views.TermsConditionEditView.as_view(), name='edit_term_condition'),
    path('terms-conditions/delete/<int:pk>/', views.TermsConditionDeleteView.as_view(), name='delete_term_condition'),

    ## Contact us
    path('contact-us/', views.ContactUsListView.as_view(), name='contact_us'),
    path('contact-us/delete/<int:pk>/', views.ContactUsDeleteView.as_view(), name='contact_delete'),


    ## Payment
    path('payment-gateway/', views.PaymentGatewayListView.as_view(), name='payment_gateway_list'),
    path('payment-gateway/add/', views.PaymentGatewayCreateView.as_view(), name='add_payment_gateway'),




    path('icons/', views.IconsView.as_view(), name='icons'),
]