from django.db import models
from django.utils import timezone
from django.conf import settings


class FileUpload(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='uploaded_files')
    title = models.CharField(max_length=200, help_text="Enter a title for the file")
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    description = models.TextField(blank=True, help_text="Optional description")
    uploaded_at = models.DateTimeField(default=timezone.now)
    file_size = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def get_file_size_display(self):
        """Return human readable file size"""
        if self.file_size:
            for unit in ['bytes', 'KB', 'MB', 'GB']:
                if self.file_size < 1024.0:
                    return f"{self.file_size:.1f} {unit}"
                self.file_size /= 1024.0
        return "Unknown size"
