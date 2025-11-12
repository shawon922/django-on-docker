from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
import os

User = get_user_model()


def get_receipt_upload_path(instance, filename):
    return f'invoices/{instance.user.id}/{filename}'


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('parsed', 'Parsed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices')
    receipt_file = models.FileField(
        upload_to=get_receipt_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'tiff'])]
    )
    original_filename = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=10, blank=True)  # 'pdf' or 'image'
    file_size = models.PositiveIntegerField(default=0)

    invoice_number = models.CharField(max_length=100, blank=True)
    merchant_name = models.CharField(max_length=255, blank=True)
    invoice_date = models.DateTimeField(blank=True, null=True)
    currency = models.CharField(max_length=10, default='SAR')

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    parse_confidence = models.FloatField(default=0.0)
    raw_text = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Invoice {self.id} - {self.merchant_name or 'Unknown'}"

    def save(self, *args, **kwargs):
        if self.receipt_file and not self.file_size:
            self.file_size = self.receipt_file.size
            self.original_filename = self.receipt_file.name
            ext = os.path.splitext(self.receipt_file.name)[1].lower()
            if ext == '.pdf':
                self.file_type = 'pdf'
            elif ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif']:
                self.file_type = 'image'
            else:
                self.file_type = 'unknown'
        super().save(*args, **kwargs)


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    position = models.PositiveIntegerField(default=0)
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    product_code = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return f"{self.description} ({self.quantity} x {self.unit_price})"

