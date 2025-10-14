from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'authentication'

urlpatterns = [
    # Authentication URLs
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    
    # Password Reset URLs
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset-complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
    # Profile URLs
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('profile/change-password/', views.change_password, name='change_password'),
    
    # Session Management URLs
    path('profile/terminate-session/<int:session_id>/', views.terminate_session, name='terminate_session'),
    path('profile/terminate-all-sessions/', views.terminate_all_sessions, name='terminate_all_sessions'),
    
    # Security URLs
    path('profile/security/', views.account_security, name='account_security'),
    path('profile/delete-account/', views.delete_account, name='delete_account'),
    
    # AJAX URLs for form validation
    path('ajax/check-username/', views.check_username_availability, name='check_username'),
    path('ajax/check-email/', views.check_email_availability, name='check_email'),
]