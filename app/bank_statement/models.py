from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from cryptography.fernet import Fernet
from django.conf import settings
import os

User = get_user_model()

def get_upload_path(instance, filename):
    """Generate secure upload path for bank statement files"""
    return f'bank_statements/{instance.user.id}/{filename}'


class Statement(models.Model):
    """Model for storing bank statement file metadata"""
    
    PROCESSING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    BANK_CHOICES = [
        ('snb', 'Saudi National Bank'),
        ('alrajhi', 'Al Rajhi Bank'),
        ('riyad', 'Riyad Bank'),
        ('sab', 'Saudi Awwal Bank'),
        ('bsf', 'Banque Saudi Fransi'),
        ('anb', 'Arab National Bank'),
        ('alinma', 'Alinma Bank'),
        ('albilad', 'Bank AlBilad'),
        ('aljazira', 'Bank AlJazira'),
        ('saib', 'Saudi Investment Bank'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bank_statements')
    file = models.FileField(
        upload_to=get_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'tiff'])]
    )
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)  # 'pdf' or 'image'
    file_size = models.PositiveIntegerField()  # in bytes
    
    bank_name = models.CharField(max_length=50, choices=BANK_CHOICES, default='other')
    account_number = models.CharField(max_length=20, blank=True, null=True)
    statement_period_start = models.DateField(blank=True, null=True)
    statement_period_end = models.DateField(blank=True, null=True)
    
    processing_status = models.CharField(max_length=20, choices=PROCESSING_STATUS_CHOICES, default='pending')
    processing_started_at = models.DateTimeField(blank=True, null=True)
    processing_completed_at = models.DateTimeField(blank=True, null=True)
    processing_error = models.TextField(blank=True, null=True)
    
    upload_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Encryption fields
    is_encrypted = models.BooleanField(default=True)
    encryption_key = models.BinaryField(blank=True, null=True)
    
    class Meta:
        ordering = ['-upload_date']
        indexes = [
            models.Index(fields=['user', 'upload_date']),
            models.Index(fields=['processing_status']),
            models.Index(fields=['bank_name']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.original_filename} ({self.bank_name})"
    
    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            # Set file metadata
            self.file_size = self.file.size
            self.original_filename = self.file.name
            
            # Determine file type based on extension
            file_extension = os.path.splitext(self.file.name)[1].lower()
            if file_extension == '.pdf':
                self.file_type = 'pdf'
            elif file_extension in ['.jpg', '.jpeg', '.png', '.tiff', '.tif']:
                self.file_type = 'image'
            else:
                self.file_type = 'unknown'
        
        if not self.encryption_key and self.is_encrypted:
            # Generate encryption key for this statement
            key = Fernet.generate_key()
            self.encryption_key = key
        super().save(*args, **kwargs)
    
    @property
    def transaction_count(self):
        return self.transactions.count()
    
    @property
    def total_debits(self):
        return self.transactions.aggregate(total=models.Sum('debit_amount'))['total'] or 0
    
    @property
    def total_credits(self):
        return self.transactions.aggregate(total=models.Sum('credit_amount'))['total'] or 0


class Transaction(models.Model):
    """Model for storing individual transaction data extracted from bank statements"""
    
    TRANSACTION_TYPE_CHOICES = [
        ('debit', 'Debit'),
        ('credit', 'Credit'),
    ]
    
    CATEGORY_CHOICES = [
        ('atm_withdrawal', 'ATM Withdrawal'),
        ('pos_purchase', 'POS Purchase'),
        ('online_transfer', 'Online Transfer'),
        ('neft', 'NEFT'),
        ('rtgs', 'RTGS'),
        ('imps', 'IMPS'),
        ('upi', 'UPI'),
        ('cheque', 'Cheque'),
        ('salary', 'Salary'),
        ('interest', 'Interest'),
        ('charges', 'Bank Charges'),
        ('refund', 'Refund'),
        ('other', 'Other'),
    ]
    
    statement = models.ForeignKey(Statement, on_delete=models.CASCADE, related_name='transactions')
    
    # Core transaction fields
    transaction_date = models.DateField()
    value_date = models.DateField(blank=True, null=True)
    description = models.TextField()
    reference_number = models.CharField(max_length=50, blank=True, null=True)
    
    # Amount fields
    debit_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    credit_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    
    # Categorization
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    
    # Data quality fields
    raw_description = models.TextField()  # Original OCR/PDF extracted text
    confidence_score = models.FloatField(default=0.0)  # OCR confidence or parsing confidence
    is_verified = models.BooleanField(default=False)
    needs_review = models.BooleanField(default=False)
    
    # Metadata
    extracted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-transaction_date', '-extracted_at']
        indexes = [
            models.Index(fields=['statement', 'transaction_date']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['category']),
            models.Index(fields=['needs_review']),
        ]
        unique_together = ['statement', 'transaction_date', 'description', 'debit_amount', 'credit_amount']
    
    def __str__(self):
        amount = self.debit_amount if self.debit_amount else self.credit_amount
        return f"{self.transaction_date} - {self.description[:50]} - {amount}"
    
    def save(self, *args, **kwargs):
        # Auto-determine transaction type based on amounts
        if self.debit_amount and self.debit_amount > 0:
            self.transaction_type = 'debit'
        elif self.credit_amount and self.credit_amount > 0:
            self.transaction_type = 'credit'
        
        # Auto-categorize based on description
        if not self.category or self.category == 'other':
            self.category = self._auto_categorize()
        
        super().save(*args, **kwargs)
    
    def _auto_categorize(self):
        """Auto-categorize transaction based on description"""
        description_lower = self.description.lower()
        
        # ATM withdrawals
        if any(keyword in description_lower for keyword in ['atm', 'cash withdrawal', 'atm wdl']):
            return 'atm_withdrawal'
        
        # POS purchases
        if any(keyword in description_lower for keyword in ['pos', 'purchase', 'merchant']):
            return 'pos_purchase'
        
        # UPI transactions
        if any(keyword in description_lower for keyword in ['upi', 'paytm', 'gpay', 'phonepe', 'bhim']):
            return 'upi'
        
        # NEFT/RTGS/IMPS
        if 'neft' in description_lower:
            return 'neft'
        if 'rtgs' in description_lower:
            return 'rtgs'
        if 'imps' in description_lower:
            return 'imps'
        
        # Salary
        if any(keyword in description_lower for keyword in ['salary', 'sal cr', 'payroll']):
            return 'salary'
        
        # Interest
        if any(keyword in description_lower for keyword in ['interest', 'int cr', 'int paid']):
            return 'interest'
        
        # Bank charges
        if any(keyword in description_lower for keyword in ['charges', 'fee', 'service charge', 'annual fee']):
            return 'charges'
        
        # Cheque
        if any(keyword in description_lower for keyword in ['cheque', 'chq', 'check']):
            return 'cheque'
        
        return 'other'
    
    @property
    def amount(self):
        """Return the transaction amount (positive for credit, negative for debit)"""
        if self.credit_amount:
            return self.credit_amount
        elif self.debit_amount:
            return -self.debit_amount
        return 0


class ProcessingLog(models.Model):
    """Model for logging processing steps and errors"""
    
    LOG_LEVEL_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]
    
    statement = models.ForeignKey(Statement, on_delete=models.CASCADE, related_name='processing_logs')
    level = models.CharField(max_length=10, choices=LOG_LEVEL_CHOICES)
    message = models.TextField()
    details = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.statement} - {self.level} - {self.message[:50]}"
