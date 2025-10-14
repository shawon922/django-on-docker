from django import forms
from django.core.validators import FileExtensionValidator
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, Div, HTML, Submit
from crispy_forms.bootstrap import FormActions
from .models import Statement, Transaction


class StatementUploadForm(forms.ModelForm):
    """Form for uploading bank statement files with drag-and-drop support"""
    
    class Meta:
        model = Statement
        fields = ['file', 'bank_name', 'account_number', 'statement_period_start', 'statement_period_end']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png,.tiff',
                'id': 'file-upload'
            }),
            'bank_name': forms.Select(attrs={'class': 'form-select'}),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter account number (optional)'
            }),
            'statement_period_start': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'statement_period_end': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.form_class = 'needs-validation'
        self.helper.attrs = {'novalidate': ''}
        
        self.helper.layout = Layout(
            HTML('''
                <div class="upload-area" id="upload-area">
                    <div class="upload-content">
                        <i class="fas fa-cloud-upload-alt fa-3x text-primary mb-3"></i>
                        <h5>Drag & Drop your bank statement here</h5>
                        <p class="text-muted">or click to browse files</p>
                        <p class="small text-muted">Supported formats: PDF, JPG, PNG, TIFF (Max 50MB)</p>
                    </div>
                </div>
            '''),
            Field('file', css_class='d-none'),
            Div(
                Div(
                    Field('bank_name', wrapper_class='mb-3'),
                    css_class='col-md-6'
                ),
                Div(
                    Field('account_number', wrapper_class='mb-3'),
                    css_class='col-md-6'
                ),
                css_class='row'
            ),
            Div(
                Div(
                    Field('statement_period_start', wrapper_class='mb-3'),
                    css_class='col-md-6'
                ),
                Div(
                    Field('statement_period_end', wrapper_class='mb-3'),
                    css_class='col-md-6'
                ),
                css_class='row'
            ),
            FormActions(
                Submit('submit', 'Upload & Process Statement', css_class='btn btn-primary btn-lg'),
                css_class='text-center mt-4'
            )
        )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (50MB limit)
            if file.size > 50 * 1024 * 1024:
                raise forms.ValidationError('File size cannot exceed 50MB.')
            
            # Check file extension
            allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'tiff']
            file_extension = file.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                raise forms.ValidationError(
                    f'Unsupported file format. Allowed formats: {", ".join(allowed_extensions)}'
                )
        return file
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('statement_period_start')
        end_date = cleaned_data.get('statement_period_end')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError('Statement period start date cannot be after end date.')
        
        return cleaned_data


class TransactionFilterForm(forms.Form):
    """Form for filtering transactions in the dashboard"""
    
    SORT_CHOICES = [
        ('-transaction_date', 'Date (Newest First)'),
        ('transaction_date', 'Date (Oldest First)'),
        ('-debit_amount', 'Debit Amount (High to Low)'),
        ('-credit_amount', 'Credit Amount (High to Low)'),
        ('description', 'Description (A-Z)'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search transactions...',
            'id': 'search-input'
        })
    )
    
    category = forms.ChoiceField(
        required=False,
        choices=[('', 'All Categories')] + Transaction.CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    transaction_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types'), ('debit', 'Debit'), ('credit', 'Credit')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    amount_min = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min amount',
            'step': '0.01'
        })
    )
    
    amount_max = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max amount',
            'step': '0.01'
        })
    )
    
    sort_by = forms.ChoiceField(
        required=False,
        choices=SORT_CHOICES,
        initial='-transaction_date',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    needs_review = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'filter-form'
        self.helper.disable_csrf = True
        
        self.helper.layout = Layout(
            Div(
                Div(
                    Field('search', wrapper_class='mb-3'),
                    css_class='col-md-4'
                ),
                Div(
                    Field('category', wrapper_class='mb-3'),
                    css_class='col-md-2'
                ),
                Div(
                    Field('transaction_type', wrapper_class='mb-3'),
                    css_class='col-md-2'
                ),
                Div(
                    Field('sort_by', wrapper_class='mb-3'),
                    css_class='col-md-2'
                ),
                Div(
                    HTML('<label class="form-label">Needs Review</label>'),
                    Field('needs_review', wrapper_class='form-check'),
                    css_class='col-md-2'
                ),
                css_class='row'
            ),
            Div(
                Div(
                    Field('date_from', wrapper_class='mb-3'),
                    css_class='col-md-3'
                ),
                Div(
                    Field('date_to', wrapper_class='mb-3'),
                    css_class='col-md-3'
                ),
                Div(
                    Field('amount_min', wrapper_class='mb-3'),
                    css_class='col-md-3'
                ),
                Div(
                    Field('amount_max', wrapper_class='mb-3'),
                    css_class='col-md-3'
                ),
                css_class='row'
            ),
            FormActions(
                Submit('filter', 'Apply Filters', css_class='btn btn-primary'),
                HTML('<a href="?" class="btn btn-outline-secondary ms-2">Clear Filters</a>'),
                css_class='text-center'
            )
        )


class TransactionEditForm(forms.ModelForm):
    """Form for editing individual transactions"""
    
    class Meta:
        model = Transaction
        fields = [
            'transaction_date', 'description', 'debit_amount', 'credit_amount',
            'balance', 'category', 'reference_number', 'is_verified'
        ]
        widgets = {
            'transaction_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'debit_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'credit_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'balance': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Reference number'
            }),
            'is_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        
        self.helper.layout = Layout(
            Fieldset(
                'Transaction Details',
                Div(
                    Div(
                        Field('transaction_date', wrapper_class='mb-3'),
                        css_class='col-md-6'
                    ),
                    Div(
                        Field('reference_number', wrapper_class='mb-3'),
                        css_class='col-md-6'
                    ),
                    css_class='row'
                ),
                Field('description', wrapper_class='mb-3'),
            ),
            Fieldset(
                'Amounts',
                Div(
                    Div(
                        Field('debit_amount', wrapper_class='mb-3'),
                        css_class='col-md-4'
                    ),
                    Div(
                        Field('credit_amount', wrapper_class='mb-3'),
                        css_class='col-md-4'
                    ),
                    Div(
                        Field('balance', wrapper_class='mb-3'),
                        css_class='col-md-4'
                    ),
                    css_class='row'
                )
            ),
            Fieldset(
                'Categorization',
                Div(
                    Div(
                        Field('category', wrapper_class='mb-3'),
                        css_class='col-md-6'
                    ),
                    Div(
                        HTML('<label class="form-label">Verified</label>'),
                        Field('is_verified', wrapper_class='form-check'),
                        css_class='col-md-6'
                    ),
                    css_class='row'
                )
            ),
            FormActions(
                Submit('save', 'Save Changes', css_class='btn btn-primary'),
                HTML('<a href="{% url \'bank_statement:dashboard\' %}" class="btn btn-outline-secondary ms-2">Cancel</a>'),
                css_class='text-center mt-4'
            )
        )


class ExportForm(forms.Form):
    """Form for exporting transaction data"""
    
    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('excel', 'Excel (XLSX)'),
        ('json', 'JSON'),
    ]
    
    format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    include_all = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Include all transactions or only filtered results'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'export-form'
        
        self.helper.layout = Layout(
            Field('format', wrapper_class='mb-3'),
            Div(
                HTML('<label class="form-label">Include All Transactions</label>'),
                Field('include_all', wrapper_class='form-check'),
                css_class='mb-3'
            ),
            FormActions(
                Submit('export', 'Export Data', css_class='btn btn-success'),
                css_class='text-center'
            )
        )