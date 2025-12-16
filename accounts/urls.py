from django.urls import path
from . import views



urlpatterns = [
    # Company Transaction URLs
    path('company-transactions/', views.CompanyTransactionListAPIView.as_view(), name='company-transaction-list'),
    path('company-transactions/create/', views.CompanyTransactionCreateAPIView.as_view(), name='company-transaction-create'),
    path('company-transactions/<int:pk>/', views.CompanyTransactionRetrieveUpdateDestroyAPIView.as_view(), name='company-transaction-detail'),

    # Personal (User) Payment Transaction URLs
    path('personal-transactions/create/', views.PersonalTransactionListCreateAPIView.as_view(), name='personal-transaction-list-create'),
    path('personal-transactions/<int:pk>/', views.PersonalTransactions.as_view(), name='personal-transaction-detail'),
    path('personal-transactions/edit/<int:pk>/', views.PersonalTransactionRetrieveUpdateDestroyAPIView.as_view(), name='personal-transaction-detail'),

    # Partners URL
    path('partners/', views.PartnerListAPIView.as_view(), name='partner-list'),

    
]
