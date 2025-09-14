from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404
from django_sendfile import sendfile
from .models import FileUpload
from .forms import FileUploadForm


def upload_file(request):
    """Handle file upload"""
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'File uploaded successfully!')
            return redirect('upload:file_list')
    else:
        form = FileUploadForm()

    return render(request, 'upload/upload_form.html', {'form': form})


def file_list(request):
    """Display list of uploaded files"""
    files = FileUpload.objects.all()
    paginator = Paginator(files, 10)  # Show 10 files per page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'upload/file_list.html', {'page_obj': page_obj})


def file_detail(request, pk):
    """Display file details"""
    try:
        file_upload = FileUpload.objects.get(pk=pk)
    except FileUpload.DoesNotExist:
        messages.error(request, 'File not found.')
        return redirect('upload:file_list')

    return render(request, 'upload/file_detail.html', {'file': file_upload})


def secure_download(request, pk):
    """Secure file download using django-sendfile"""
    file_upload = get_object_or_404(FileUpload, pk=pk)

    # You can add additional security checks here
    # For example: user authentication, permissions, etc.

    if not file_upload.file:
        raise Http404("File not found")

    # Use sendfile to serve the file securely
    response = sendfile(request, file_upload.file.path, attachment=True, attachment_filename=file_upload.title)
    return response
