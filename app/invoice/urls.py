from django.urls import path
from . import views

app_name = 'invoice'

urlpatterns = [
    path('', views.invoice_list, name='list'),
    path('upload/', views.upload_receipt, name='upload'),
    path('<int:pk>/', views.invoice_detail, name='detail'),
]
