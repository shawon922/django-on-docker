from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Statement, Transaction, ProcessingLog


@admin.register(Statement)
class StatementAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'original_filename', 'bank_name', 
        'processing_status', 'transaction_count', 'upload_date'
    ]
    list_filter = [
        'processing_status', 'bank_name', 'file_type', 
        'upload_date', 'is_encrypted'
    ]
    search_fields = [
        'user__username', 'user__email', 'original_filename', 
        'account_number'
    ]
    readonly_fields = [
        'file_size', 'upload_date', 'updated_at', 
        'processing_started_at', 'processing_completed_at',
        'transaction_count', 'total_debits', 'total_credits'
    ]
    fieldsets = (
        ('File Information', {
            'fields': ('user', 'file', 'original_filename', 'file_type', 'file_size')
        }),
        ('Bank Details', {
            'fields': ('bank_name', 'account_number', 'statement_period_start', 'statement_period_end')
        }),
        ('Processing Status', {
            'fields': ('processing_status', 'processing_started_at', 'processing_completed_at', 'processing_error')
        }),
        ('Security', {
            'fields': ('is_encrypted', 'encryption_key'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('transaction_count', 'total_debits', 'total_credits'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('upload_date', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def transaction_count(self, obj):
        count = obj.transaction_count
        if count > 0:
            url = reverse('admin:bank_statement_transaction_changelist') + f'?statement__id={obj.id}'
            return format_html('<a href="{}">{} transactions</a>', url, count)
        return '0 transactions'
    transaction_count.short_description = 'Transactions'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ['extracted_at', 'updated_at']
    fields = [
        'transaction_date', 'description', 'debit_amount', 
        'credit_amount', 'balance', 'category', 'is_verified'
    ]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'statement_link', 'transaction_date', 'description_short',
        'debit_amount', 'credit_amount', 'category', 'is_verified', 'needs_review'
    ]
    list_filter = [
        'transaction_type', 'category', 'is_verified', 'needs_review',
        'transaction_date', 'extracted_at'
    ]
    search_fields = [
        'description', 'raw_description', 'reference_number',
        'statement__user__username'
    ]
    readonly_fields = [
        'extracted_at', 'updated_at', 'confidence_score'
    ]
    fieldsets = (
        ('Transaction Details', {
            'fields': (
                'statement', 'transaction_date', 'value_date',
                'description', 'reference_number'
            )
        }),
        ('Amounts', {
            'fields': ('debit_amount', 'credit_amount', 'balance')
        }),
        ('Categorization', {
            'fields': ('transaction_type', 'category')
        }),
        ('Data Quality', {
            'fields': (
                'raw_description', 'confidence_score', 
                'is_verified', 'needs_review'
            )
        }),
        ('Timestamps', {
            'fields': ('extracted_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def statement_link(self, obj):
        url = reverse('admin:bank_statement_statement_change', args=[obj.statement.id])
        return format_html('<a href="{}">{}</a>', url, obj.statement.original_filename)
    statement_link.short_description = 'Statement'
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('statement', 'statement__user')


@admin.register(ProcessingLog)
class ProcessingLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'statement_link', 'level', 'message_short', 'timestamp'
    ]
    list_filter = ['level', 'timestamp']
    search_fields = ['message', 'statement__original_filename']
    readonly_fields = ['timestamp']
    
    def statement_link(self, obj):
        url = reverse('admin:bank_statement_statement_change', args=[obj.statement.id])
        return format_html('<a href="{}">{}</a>', url, obj.statement.original_filename)
    statement_link.short_description = 'Statement'
    
    def message_short(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_short.short_description = 'Message'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('statement')


# Add inline to Statement admin
StatementAdmin.inlines = [TransactionInline]
