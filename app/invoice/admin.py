from django.contrib import admin
from .models import Invoice, InvoiceLine


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "merchant_name", "invoice_date", "total_amount", "status")
    list_filter = ("status", "invoice_date")
    search_fields = ("merchant_name", "invoice_number", "original_filename")
    inlines = [InvoiceLineInline]

