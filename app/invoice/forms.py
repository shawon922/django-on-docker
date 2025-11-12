from django import forms
from .models import Invoice


class InvoiceUploadForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["receipt_file"]

