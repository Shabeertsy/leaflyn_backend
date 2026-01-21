from django.urls import path
from . import views



urlpatterns = [

    path('login/', views.LoginView.as_view(), name='auth-login'),


    # Transaction Request URLs
    path('transaction-requests/', views.TransactionRequestsListAPIView.as_view(), name='transaction-request-list'),
    path('transaction-requests/<int:pk>/approve/', views.ApproveTransactionAPIView.as_view(), name='transaction-request-approve'),
    path('my-requests/', views.MyTransactionRequestsListAPIView.as_view(), name='my-transaction-request-list'),


    # Company Transaction URLs
    path('company-transactions/', views.CompanyTransactionListAPIView.as_view(), name='company-transaction-list'),
    path('company-transactions/create/', views.CompanyTransactionCreateAPIView.as_view(), name='company-transaction-create'),
    path('company-transactions/<int:pk>/', views.CompanyTransactionRetrieveUpdateDestroyAPIView.as_view(), name='company-transaction-detail'),

    # Split Transaction URLs
    path('split-transactions/', views.SplitTransactionListAPIView.as_view(), name='split-transaction-list'),




    # Personal (User) Payment Transaction URLs
    path('personal-transactions/create/', views.UserPaymentCreateAPIView.as_view(), name='personal-transaction-list-create'),
    path('personal-transactions/<int:pk>/', views.PersonalTransactions.as_view(), name='personal-transaction-detail'),
    path('personal-transactions/edit/<int:pk>/', views.UserPaymentRetrieveUpdateDestroyAPIView.as_view(), name='personal-transaction-detail'),


    # Partners URL
    path('partners/', views.PartnerListAPIView.as_view(), name='partner-list'),


    # Partner Transactions URL
    path('partners/transactions/', views.PartnerTransactionsListAPIView.as_view(), name='partner-transactions-list'),

    ## personal transactions 
    path('personal-transactions/details/<int:partner>/<int:transaction>/', views.PartnerTransactionsInnerPage.as_view(), name='personal-transactions-detail'),

    # Todo URLs
    path('todos/', views.TodoListCreateAPIView.as_view(), name='todo-list-create'),
    path('todos/<int:pk>/', views.TodoRetrieveUpdateDestroyAPIView.as_view(), name='todo-detail'),


    ## client 
    path('clients/', views.ClientListCreateAPIView.as_view(), name='client-list-create'),
    path('clients/<int:pk>/', views.ClientRetrieveUpdateDestroyAPIView.as_view(), name='client-detail'),


    ## service
    path('services/', views.ServiceListCreateAPIView.as_view(), name='service-list-create'),
    path('services/<int:pk>/', views.ServiceRetrieveUpdateDestroyAPIView.as_view(), name='service-detail'),


    ## service transaction
    path('service-transactions/', views.ServiceTransactionListCreateAPIView.as_view(), name='service-transaction-list-create'),
    path('service-transactions/<int:pk>/', views.ServiceTransactionRetrieveUpdateDestroyAPIView.as_view(), name='service-transaction-detail'),
    path('clients/<int:client_id>/transactions/', views.ServiceTransactionsByClientAPIView.as_view(), name='service-transactions-by-client'),
    path('services/<int:service_id>/transactions/', views.ServiceTransactionsByServiceAPIView.as_view(), name='service-transactions-by-service'),


]
