from django.urls import path
from . import views

app_name = 'upload'

urlpatterns = [
    path('', views.file_list, name='file_list'),
    path('upload/', views.upload_file, name='upload_file'),
    path('file/<int:pk>/', views.file_detail, name='file_detail'),
    path('download/<int:pk>/', views.secure_download, name='secure_download'),
]
