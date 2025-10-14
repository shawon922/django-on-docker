from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, UpdateView, DetailView
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponseRedirect
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm, CustomPasswordResetForm,
    CustomSetPasswordForm, UserProfileForm, ChangePasswordForm
)
from .models import User
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


class CustomLoginView(LoginView):
    """
    Custom login view with enhanced security and user experience
    """
    form_class = CustomAuthenticationForm
    template_name = 'authentication/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('bank_statement:dashboard')
    
    def form_valid(self, form):
        """Handle successful login"""
        user = form.get_user()
        
        # Handle remember me functionality
        remember_me = form.cleaned_data.get('remember_me')
        if remember_me:
            self.request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days
        else:
            self.request.session.set_expiry(0)  # Browser session
        
        messages.success(self.request, f'Welcome back, {user.get_full_name() or user.username}!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Handle failed login attempts"""
        # Failed login attempt - simplified logging removed
        messages.error(self.request, 'Invalid email or password. Please try again.')
        return super().form_invalid(form)
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class CustomLogoutView(LogoutView):
    """
    Custom logout view with session cleanup
    """
    template_name = 'authentication/logout.html'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.success(request, 'You have been successfully logged out.')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_next_page(self):
        return reverse_lazy('authentication:login')


class RegisterView(CreateView):
    """
    User registration view
    """
    model = User
    form_class = CustomUserCreationForm
    template_name = 'authentication/register.html'
    success_url = reverse_lazy('authentication:login')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('bank_statement:dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """Handle successful registration"""
        with transaction.atomic():
            user = form.save()
            
            # Send welcome email
            self.send_welcome_email(user)
            
            # Log registration
            logger.info(f'New user registered: {user.email}')
            
            messages.success(
                self.request,
                f'Welcome {user.get_full_name()}! Your account has been created successfully. '
                'Please log in to continue.'
            )
            
        return super().form_valid(form)
    
    def send_welcome_email(self, user):
        """Send welcome email to new user"""
        try:
            subject = 'Welcome to Bank Statement Analyzer'
            html_message = render_to_string('authentication/emails/welcome.html', {
                'user': user,
                'site_name': 'Bank Statement Analyzer'
            })
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=True
            )
        except Exception as e:
            logger.error(f'Failed to send welcome email to {user.email}: {str(e)}')


class CustomPasswordResetView(PasswordResetView):
    """
    Custom password reset view
    """
    form_class = CustomPasswordResetForm
    template_name = 'authentication/password_reset.html'
    email_template_name = 'authentication/emails/password_reset.html'
    subject_template_name = 'authentication/emails/password_reset_subject.txt'
    success_url = reverse_lazy('authentication:password_reset_done')
    
    def form_valid(self, form):
        messages.success(
            self.request,
            'Password reset instructions have been sent to your email address.'
        )
        return super().form_valid(form)


class CustomPasswordResetDoneView(PasswordResetDoneView):
    """
    Password reset done view
    """
    template_name = 'authentication/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    """
    Password reset confirm view
    """
    form_class = CustomSetPasswordForm
    template_name = 'authentication/password_reset_confirm.html'
    success_url = reverse_lazy('authentication:password_reset_complete')
    
    def form_valid(self, form):
        messages.success(
            self.request,
            'Your password has been reset successfully. You can now log in with your new password.'
        )
        return super().form_valid(form)


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    """
    Password reset complete view
    """
    template_name = 'authentication/password_reset_complete.html'


@method_decorator([login_required, never_cache], name='dispatch')
class ProfileView(DetailView):
    """
    User profile view
    """
    model = User
    template_name = 'authentication/profile.html'
    context_object_name = 'profile_user'
    
    def get_object(self):
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        # Minimal profile context - no session tracking
        context['recent_logins'] = []
        context['active_sessions'] = []
        
        return context


@method_decorator([login_required, never_cache], name='dispatch')
class ProfileEditView(UpdateView):
    """
    Edit user profile view
    """
    model = User
    form_class = UserProfileForm
    template_name = 'authentication/profile_edit.html'
    
    def get_object(self):
        return self.request.user
    
    def get_success_url(self):
        return reverse_lazy('authentication:profile')
    
    def form_valid(self, form):
        messages.success(self.request, 'Your profile has been updated successfully.')
        return super().form_valid(form)


@login_required
@csrf_protect
def change_password(request):
    """
    Change password view
    """
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('authentication:profile')
    else:
        form = ChangePasswordForm(request.user)
    
    return render(request, 'authentication/change_password.html', {'form': form})


@login_required
def terminate_session(request, session_id):
    """
    Session termination not available in minimal setup
    """
    messages.info(request, 'Session management not available in minimal setup.')
    return redirect('authentication:profile')


@login_required
def terminate_all_sessions(request):
    """
    Session termination not available in minimal setup
    """
    messages.info(request, 'Session management not available in minimal setup.')
    return redirect('authentication:profile')


def check_username_availability(request):
    """
    AJAX view to check username availability
    """
    username = request.GET.get('username', '')
    
    if len(username) < 3:
        return JsonResponse({
            'available': False,
            'message': 'Username must be at least 3 characters long.'
        })
    
    is_available = not User.objects.filter(username=username).exists()
    
    return JsonResponse({
        'available': is_available,
        'message': 'Username is available.' if is_available else 'Username is already taken.'
    })


def check_email_availability(request):
    """
    AJAX view to check email availability
    """
    email = request.GET.get('email', '')
    user_id = request.GET.get('user_id', None)
    
    if not email:
        return JsonResponse({
            'available': False,
            'message': 'Email is required.'
        })
    
    query = User.objects.filter(email=email)
    if user_id:
        query = query.exclude(id=user_id)
    
    is_available = not query.exists()
    
    return JsonResponse({
        'available': is_available,
        'message': 'Email is available.' if is_available else 'Email is already registered.'
    })


@login_required
def account_security(request):
    """
    Account security dashboard - minimal setup
    """
    user = request.user
    
    # Minimal security context - no tracking
    context = {
        'recent_attempts': [],
        'failed_attempts_24h': 0,
        'active_sessions': [],
        'current_session_key': request.session.session_key,
    }
    
    return render(request, 'authentication/account_security.html', context)


@login_required
def delete_account(request):
    """
    Account deletion view
    """
    if request.method == 'POST':
        password = request.POST.get('password')
        
        if request.user.check_password(password):
            # Log account deletion
            logger.info(f'User account deleted: {request.user.email}')
            
            # Delete user account
            request.user.delete()
            
            messages.success(request, 'Your account has been deleted successfully.')
            return redirect('authentication:login')
        else:
            messages.error(request, 'Incorrect password. Account deletion cancelled.')
    
    return render(request, 'authentication/delete_account.html')
