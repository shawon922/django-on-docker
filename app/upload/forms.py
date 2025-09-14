from django import forms
from .models import FileUpload


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = FileUpload
        fields = ['title', 'file', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter file title'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '*/*'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description'
            })
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Limit file size to 10MB
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 10MB.')
        return file
