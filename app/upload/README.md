# File Upload System

A secure file upload and management system built for the Django on Docker application with user authentication and secure file serving.

## Features

### Core Functionality
- **File Upload**: Simple form-based file upload interface
- **File Management**: List, view, and download uploaded files
- **Secure Downloads**: Files served through Django views with access control using django-sendfile2
- **User-specific Files**: Each user can only access their own uploaded files

### User Interface
- **Responsive Design**: Bootstrap-based UI that works on all devices
- **File List**: Paginated list of all uploaded files
- **File Details**: Detailed view of each file with metadata
- **Upload Form**: User-friendly form with validation

### Technical Features
- **Security**: File validation, CSRF protection, and secure downloads
- **Pagination**: Efficient handling of large file collections
- **File Size Display**: Human-readable file size formatting
- **Access Control**: Login required for all operations

## Installation

1. **Add to INSTALLED_APPS**:
   ```python
   INSTALLED_APPS = [
       # ... other apps
       'upload',
   ]
   ```

2. **Include URLs**:
   ```python
   urlpatterns = [
       path('upload/', include('upload.urls')),
       # ... other patterns
   ]
   ```

3. **Run Migrations**:
   ```bash
   python manage.py makemigrations upload
   python manage.py migrate
   ```

## Configuration

### Required Settings

```python
# Media Settings
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Django-sendfile2 Settings
SENDFILE_BACKEND = 'django_sendfile.backends.nginx'  # For production with Nginx
# SENDFILE_BACKEND = 'django_sendfile.backends.development'  # For development
SENDFILE_ROOT = os.path.join(BASE_DIR, 'media')
SENDFILE_URL = '/media/'
```

### Nginx Configuration (for production)

```nginx
location /media/ {
    internal;
    alias /path/to/media/;
}
```

## URL Patterns

| URL | View | Description |
|-----|------|-------------|
| `/upload/` | file_list | List all uploaded files |
| `/upload/upload/` | upload_file | Upload new file |
| `/upload/file/<id>/` | file_detail | View file details |
| `/upload/download/<id>/` | secure_download | Securely download file |

## Models

### FileUpload

Stores uploaded file information and metadata:

```python
class FileUpload(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_files')
    title = models.CharField(max_length=200, help_text="Enter a title for the file")
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    description = models.TextField(blank=True, help_text="Optional description")
    uploaded_at = models.DateTimeField(default=timezone.now)
    file_size = models.PositiveIntegerField(null=True, blank=True)
```

## Forms

### FileUploadForm

Handles file upload with validation:

```python
class FileUploadForm(forms.ModelForm):
    class Meta:
        model = FileUpload
        fields = ['title', 'file', 'description']
```

## Views

- **upload_file**: Handle file upload form submission
- **file_list**: Display paginated list of user's files
- **file_detail**: Show detailed information about a file
- **secure_download**: Securely serve file downloads

## Templates

- `upload/upload_form.html` - File upload form
- `upload/file_list.html` - List of uploaded files
- `upload/file_detail.html` - File details view

## Security Features

- **Authentication Required**: All views require login
- **User Isolation**: Users can only access their own files
- **Secure Downloads**: Files served through django-sendfile2
- **CSRF Protection**: All forms protected against CSRF

## Usage Examples

### Uploading a File

```python
from upload.models import FileUpload
from django.core.files import File

with open('example.txt', 'rb') as f:
    file_upload = FileUpload(
        user=request.user,
        title='Example File',
        description='An example file upload'
    )
    file_upload.file.save('example.txt', File(f))
    file_upload.save()
```

### Retrieving User's Files

```python
from upload.models import FileUpload

# Get all files for current user
user_files = FileUpload.objects.filter(user=request.user)

# Get most recent files
recent_files = FileUpload.objects.filter(user=request.user).order_by('-uploaded_at')[:5]
```

## Troubleshooting

### Common Issues

1. **File upload errors**:
   - Check file size limits in settings
   - Verify media directory permissions

2. **Download issues**:
   - Ensure django-sendfile2 is properly configured
   - Check Nginx configuration for production

3. **Permission errors**:
   - Verify user authentication is working
   - Check file ownership and permissions

## Contributing

1. Follow Django coding standards
2. Add tests for new features
3. Update documentation
4. Ensure security best practices

## License

This file upload system is part of the Django on Docker application.