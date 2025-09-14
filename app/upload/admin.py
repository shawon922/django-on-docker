from django.contrib import admin
from .models import FileUpload


@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = ['title', 'file', 'uploaded_at', 'get_file_size_display']
    list_filter = ['uploaded_at']
    search_fields = ['title', 'description']
    readonly_fields = ['uploaded_at', 'file_size']

    def get_file_size_display(self, obj):
        return obj.get_file_size_display()
    get_file_size_display.short_description = 'File Size'
