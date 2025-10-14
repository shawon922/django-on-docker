# Django Authentication System

A comprehensive authentication system built for the Django on Docker application with modern security features and responsive UI.

## Features

### Core Authentication
- **Custom User Model**: Minimal Django user model with email authentication
- **User Registration**: Simple registration with email as username
- **Login/Logout**: Basic session-based authentication
- **Password Reset**: Email-based password reset functionality
- **Profile Management**: Basic user profile editing

### Security Features
- **Email Authentication**: Uses email as the primary login identifier
- **Security Headers**: CSRF, XSS, and other security protections
- **Secure Cookies**: HTTPOnly and Secure cookie settings

### User Interface
- **Responsive Design**: Mobile-first Bootstrap-based UI
- **Modern Styling**: Clean, professional interface
- **Interactive Elements**: Password strength indicators, form validation
- **Accessibility**: ARIA labels and keyboard navigation support
- **Dark Mode**: Automatic dark mode detection

## Installation

1. **Add to INSTALLED_APPS**:
   ```python
   INSTALLED_APPS = [
       # ... other apps
       'authentication',
   ]
   ```

2. **Update AUTH_USER_MODEL**:
   ```python
   AUTH_USER_MODEL = 'authentication.User'
   ```

3. **Include URLs**:
   ```python
   urlpatterns = [
       path('auth/', include('authentication.urls')),
       # ... other patterns
   ]
   ```

4. **Run Migrations**:
   ```bash
   python manage.py makemigrations authentication
   python manage.py migrate
   ```

## Configuration

### Required Settings

```python
# Authentication Settings
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'

# Session Settings
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Email Settings (for password reset)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'your-smtp-host'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email'
EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
```

### Optional Settings

```python
# Account Security
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 1800  # 30 minutes
PASSWORD_HISTORY_COUNT = 5
FORCE_PASSWORD_CHANGE_DAYS = 90

# Two-Factor Authentication
TWO_FACTOR_ENABLED = True
TWO_FACTOR_BACKUP_TOKENS = 10

# Password Reset
PASSWORD_RESET_TIMEOUT = 3600  # 1 hour

# Email Verification
EMAIL_VERIFICATION_TIMEOUT = 86400  # 24 hours
```

## URL Patterns

| URL | View | Description |
|-----|------|-------------|
| `/auth/login/` | Login | User login page |
| `/auth/logout/` | Logout | User logout |
| `/auth/register/` | Register | User registration |
| `/auth/password-reset/` | Password Reset | Request password reset |
| `/auth/password-reset/done/` | Reset Done | Password reset sent confirmation |
| `/auth/reset/<uidb64>/<token>/` | Reset Confirm | Password reset form |
| `/auth/reset/done/` | Reset Complete | Password reset success |
| `/auth/profile/` | Profile | User profile management |
| `/auth/change-password/` | Change Password | Change password form |
| `/auth/sessions/` | Sessions | Active session management |
| `/auth/terminate-session/` | Terminate Session | AJAX session termination |
| `/auth/setup-2fa/` | Setup 2FA | Two-factor authentication setup |
| `/auth/verify-2fa/` | Verify 2FA | Two-factor authentication verification |

## Templates

The authentication system includes responsive templates:

- `authentication/base.html` - Base template with Bootstrap styling
- `authentication/login.html` - Login form
- `authentication/register.html` - Registration form with validation
- `authentication/password_reset.html` - Password reset request
- `authentication/password_reset_done.html` - Reset confirmation
- `authentication/password_reset_confirm.html` - New password form
- `authentication/password_reset_complete.html` - Reset success
- `authentication/profile.html` - User profile management
- `authentication/emails/` - Email templates for notifications

## Static Assets

- `authentication/css/auth.css` - Custom authentication styles
- `authentication/js/auth.js` - Interactive JavaScript functionality
- `authentication/images/logo.svg` - Application logo

## Models

### User Model

Minimal Django user model with essential fields:

```python
class User(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
```

This simplified model focuses on core authentication functionality with email as the primary identifier.

## Forms

The system includes comprehensive forms with validation:

- `CustomUserCreationForm` - User registration
- `CustomAuthenticationForm` - User login
- `UserProfileForm` - Profile editing
- `PasswordChangeForm` - Password change
- `TwoFactorSetupForm` - 2FA setup
- `TwoFactorVerificationForm` - 2FA verification

## Security Features

### Password Security
- Minimum length requirements
- Complexity validation (uppercase, lowercase, numbers, symbols)
- Password history tracking
- Strength indicator in UI

### Account Protection
- Failed login attempt tracking
- Automatic account lockout
- Session monitoring and management
- Email notifications for security events

### Two-Factor Authentication
- TOTP-based authentication
- QR code generation for easy setup
- Backup codes for account recovery
- Optional enforcement for admin users

## Usage Examples

### Protecting Views

```python
from django.contrib.auth.decorators import login_required

@login_required
def protected_view(request):
    # Your view logic here
    pass
```

### Checking User Permissions

```python
if request.user.is_authenticated:
    # User is logged in
    # Basic authentication check for simplified user model
    pass
```

### Custom User Creation

```python
from authentication.models import User

user = User.objects.create_user(
    username='testuser',
    email='test@example.com',
    password='securepassword123',
    phone_number='+1234567890'
)
```

## Testing

Run the authentication tests:

```bash
python manage.py test authentication
```

## Troubleshooting

### Common Issues

1. **Email not sending**: Check email backend configuration
2. **Static files not loading**: Run `python manage.py collectstatic`
3. **Migration errors**: Ensure custom user model is set before initial migration
4. **Session issues**: Check session middleware configuration

### Debug Settings

For development, you can use console email backend:

```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

## Contributing

1. Follow Django coding standards
2. Add tests for new features
3. Update documentation
4. Ensure security best practices

## License

This authentication system is part of the Django on Docker application and is licensed under the MIT License.