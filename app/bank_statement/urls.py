from django.urls import path
from . import views

app_name = 'bank_statement'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Statement management
    path('upload/', views.upload_statement, name='upload_statement'),
    path('statements/', views.statement_list, name='statement_list'),
    path('statements/<int:pk>/', views.statement_detail, name='statement_detail'),
    path('statements/<int:pk>/reprocess/', views.reprocess_statement, name='reprocess_statement'),
    path('statements/<int:pk>/export/', views.export_data, name='export_data'),

    path('statements/<int:pk>/status/', views.processing_status, name='processing_status'),
    
    # Transaction management
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/<int:pk>/edit/', views.transaction_edit, name='transaction_edit'),
    path('transactions/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),

    # Export all transactions
    path('transactions/export/', views.export_all_transactions, name='export_all_transactions'),
    
    # AJAX endpoints
    path('ajax/search/', views.ajax_transaction_search, name='ajax_transaction_search'),
]