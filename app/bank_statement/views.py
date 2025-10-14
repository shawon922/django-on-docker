from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.db import transaction as db_transaction
from django.utils import timezone
from django.conf import settings
import json
import csv
import io
from datetime import datetime, date
from decimal import Decimal
import logging

from .models import Statement, Transaction, ProcessingLog
from .forms import StatementUploadForm, TransactionFilterForm, TransactionEditForm, ExportForm
from .utils import BankStatementProcessor, DataCleaner

logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    """Main dashboard view showing user's statements and recent transactions"""
    user_statements = Statement.objects.filter(user=request.user).order_by('-upload_date')
    recent_transactions = Transaction.objects.filter(
        statement__user=request.user
    ).order_by('-transaction_date')[:10]
    
    # Statistics
    total_statements = user_statements.count()
    total_transactions = Transaction.objects.filter(statement__user=request.user).count()
    total_debits = Transaction.objects.filter(
        statement__user=request.user,
        debit_amount__isnull=False
    ).aggregate(total=Sum('debit_amount'))['total'] or Decimal('0')
    total_credits = Transaction.objects.filter(
        statement__user=request.user,
        credit_amount__isnull=False
    ).aggregate(total=Sum('credit_amount'))['total'] or Decimal('0')
    
    stats = {
        'total_statements': total_statements,
        'total_transactions': total_transactions,
        'total_debits': total_debits,
        'total_credits': total_credits,
        'net_amount': total_credits - total_debits,
    }
    
    context = {
        'recent_statements': user_statements[:5],  # Template expects this
        'statements': user_statements[:5],         # Keep for backward compatibility
        'recent_transactions': recent_transactions,
        'stats': stats,
    }
    
    return render(request, 'bank_statement/dashboard.html', context)


@login_required
def upload_statement(request):
    """Handle statement file upload"""
    if request.method == 'POST':
        form = StatementUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with db_transaction.atomic():
                    statement = form.save(commit=False)
                    statement.user = request.user
                    statement.save()
                    
                    # Process the file asynchronously or synchronously based on settings
                    if getattr(settings, 'USE_CELERY', False):
                        # Import here to avoid circular imports
                        from .tasks import process_statement_task
                        process_statement_task.delay(statement.id)
                        messages.success(request, 'File uploaded successfully. Processing will begin shortly.')
                    else:
                        # Process synchronously
                        success, message = process_statement_sync(statement)
                        if success:
                            messages.success(request, message)
                        else:
                            messages.error(request, message)
                    
                    return redirect('bank_statement:statement_detail', pk=statement.pk)
            except Exception as e:
                logger.error(f"Upload failed for user {request.user.id}: {str(e)}")
                messages.error(request, f'Upload failed: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StatementUploadForm()
    
    return render(request, 'bank_statement/upload_statement.html', {'form': form})


def process_statement_sync(statement):
    """Process statement synchronously"""
    try:
        processor = BankStatementProcessor(statement)
        transactions_data = processor.process()
        
        if not transactions_data:
            return False, "No transactions found in the uploaded file."
        
        # Clean and validate transactions
        valid_transactions = []
        invalid_count = 0
        
        for trans_data in transactions_data:
            # Clean description
            trans_data['description'] = DataCleaner.clean_description(
                trans_data.get('description', '')
            )
            
            # Validate transaction
            is_valid, errors = DataCleaner.validate_transaction(trans_data)
            
            if is_valid:
                valid_transactions.append(trans_data)
            else:
                invalid_count += 1
                logger.warning(f"Invalid transaction: {errors}")
        
        # Detect duplicates
        duplicate_indices = DataCleaner.detect_duplicates(valid_transactions)
        
        # Save valid transactions
        saved_count = 0
        with db_transaction.atomic():
            for i, trans_data in enumerate(valid_transactions):
                if i not in duplicate_indices:
                    Transaction.objects.create(
                        statement=statement,
                        transaction_date=trans_data['transaction_date'],
                        description=trans_data['description'],
                        raw_description=trans_data.get('raw_description', ''),
                        debit_amount=trans_data.get('debit_amount'),
                        credit_amount=trans_data.get('credit_amount'),
                        balance=trans_data.get('balance'),
                        confidence_score=trans_data.get('confidence_score', 1.0)
                    )
                    saved_count += 1
        
        # Update statement status
        statement.processing_status = 'completed'
        statement.processing_completed_at = timezone.now()
        statement.save()
        
        message = f"Processing completed. {saved_count} transactions extracted."
        if invalid_count > 0:
            message += f" {invalid_count} invalid transactions skipped."
        if duplicate_indices:
            message += f" {len(duplicate_indices)} duplicates removed."
        
        return True, message
        
    except Exception as e:
        statement.status = 'failed'
        statement.save()
        logger.error(f"Processing failed for statement {statement.id}: {str(e)}")
        return False, f"Processing failed: {str(e)}"


@login_required
def statement_list(request):
    """List all user's statements"""
    statements = Statement.objects.filter(user=request.user).order_by('-upload_date')
    
    # Filter by status if provided
    status_filter = request.GET.get('processing_status')
    if status_filter:
        statements = statements.filter(processing_status=status_filter)
    
    # Filter by bank if provided
    bank_filter = request.GET.get('bank_name')
    if bank_filter:
        statements = statements.filter(bank_name=bank_filter)
    
    # Filter by file type if provided
    file_type_filter = request.GET.get('file_type')
    if file_type_filter:
        statements = statements.filter(file_type=file_type_filter)
    
    # Filter by search term if provided
    search_term = request.GET.get('search')
    if search_term:
        statements = statements.filter(original_filename__icontains=search_term)
    
    # Add transaction counts
    statements = statements.annotate(
        transactions_count=Count('transactions')
    )
    
    # Get statistics for the summary cards
    total_count = Statement.objects.filter(user=request.user).count()
    completed_count = Statement.objects.filter(user=request.user, processing_status='completed').count()
    processing_count = Statement.objects.filter(user=request.user, processing_status='processing').count()
    failed_count = Statement.objects.filter(user=request.user, processing_status='failed').count()
    
    # Get unique bank names for the filter dropdown
    banks = Statement.objects.filter(user=request.user).values_list('bank_name', flat=True).distinct()
    
    paginator = Paginator(statements, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'bank_statement/statement_list.html', {
        'page_obj': page_obj,
        'statements': page_obj,  # Add this to make the template work
        'total_count': total_count,
        'completed_count': completed_count,
        'processing_count': processing_count,
        'failed_count': failed_count,
        'banks': banks,
        'is_paginated': paginator.num_pages > 1  # Add this for pagination template logic
    })


@login_required
def statement_detail(request, pk):
    """View statement details and transactions"""
    statement = get_object_or_404(Statement, pk=pk, user=request.user)
    
    # Get transactions with filtering
    transactions = statement.transactions.all().order_by('-transaction_date')
    
    # Apply filters
    filter_form = TransactionFilterForm(request.GET)
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('date_from'):
            transactions = transactions.filter(
                transaction_date__gte=filter_form.cleaned_data['date_from']
            )
        if filter_form.cleaned_data.get('date_to'):
            transactions = transactions.filter(
                transaction_date__lte=filter_form.cleaned_data['date_to']
            )
        if filter_form.cleaned_data.get('transaction_type'):
            if filter_form.cleaned_data['transaction_type'] == 'debit':
                transactions = transactions.filter(debit_amount__isnull=False)
            elif filter_form.cleaned_data['transaction_type'] == 'credit':
                transactions = transactions.filter(credit_amount__isnull=False)
        if filter_form.cleaned_data.get('min_amount'):
            transactions = transactions.filter(
                Q(debit_amount__gte=filter_form.cleaned_data['min_amount']) |
                Q(credit_amount__gte=filter_form.cleaned_data['min_amount'])
            )
        if filter_form.cleaned_data.get('max_amount'):
            transactions = transactions.filter(
                Q(debit_amount__lte=filter_form.cleaned_data['max_amount']) |
                Q(credit_amount__lte=filter_form.cleaned_data['max_amount'])
            )
        if filter_form.cleaned_data.get('search_description'):
            transactions = transactions.filter(
                description__icontains=filter_form.cleaned_data['search_description']
            )
    
    # Pagination
    paginator = Paginator(transactions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics for this statement
    stats = {
        'total_transactions': statement.transactions.count(),
        'total_debits': statement.transactions.filter(
            debit_amount__isnull=False
        ).aggregate(total=Sum('debit_amount'))['total'] or Decimal('0'),
        'total_credits': statement.transactions.filter(
            credit_amount__isnull=False
        ).aggregate(total=Sum('credit_amount'))['total'] or Decimal('0'),
    }
    stats['net_amount'] = stats['total_credits'] - stats['total_debits']
    
    # Processing logs
    logs = ProcessingLog.objects.filter(statement=statement).order_by('-timestamp')[:10]
    
    context = {
        'statement': statement,
        'page_obj': page_obj,
        'transactions': page_obj,  # Template iterates over `transactions`
        'filter_form': filter_form,
        'transaction_stats': {
            'total_count': stats['total_transactions'],
            'total_debits': stats['total_debits'],
            'total_credits': stats['total_credits'],
            'net_amount': stats['net_amount'],
        },
        'logs': logs,
        'is_paginated': page_obj.paginator.num_pages > 1,
    }
    
    return render(request, 'bank_statement/statement_detail.html', context)


@login_required
def transaction_edit(request, pk):
    """Edit a transaction"""
    transaction = get_object_or_404(Transaction, pk=pk, statement__user=request.user)
    
    if request.method == 'POST':
        form = TransactionEditForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction updated successfully.')
            return redirect('bank_statement:statement_detail', pk=transaction.statement.pk)
    else:
        form = TransactionEditForm(instance=transaction)
    
    return render(request, 'bank_statement/transaction_edit.html', {
        'form': form,
        'transaction': transaction
    })


@login_required
def transaction_list(request):
    """Browse all transactions across user's statements"""
    transactions = Transaction.objects.filter(statement__user=request.user).order_by('-transaction_date')
    
    filter_form = TransactionFilterForm(request.GET)
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('date_from'):
            transactions = transactions.filter(transaction_date__gte=filter_form.cleaned_data['date_from'])
        if filter_form.cleaned_data.get('date_to'):
            transactions = transactions.filter(transaction_date__lte=filter_form.cleaned_data['date_to'])
        if filter_form.cleaned_data.get('transaction_type'):
            if filter_form.cleaned_data['transaction_type'] == 'debit':
                transactions = transactions.filter(debit_amount__isnull=False)
            elif filter_form.cleaned_data['transaction_type'] == 'credit':
                transactions = transactions.filter(credit_amount__isnull=False)
        if filter_form.cleaned_data.get('min_amount'):
            transactions = transactions.filter(
                Q(debit_amount__gte=filter_form.cleaned_data['min_amount']) |
                Q(credit_amount__gte=filter_form.cleaned_data['min_amount'])
            )
        if filter_form.cleaned_data.get('max_amount'):
            transactions = transactions.filter(
                Q(debit_amount__lte=filter_form.cleaned_data['max_amount']) |
                Q(credit_amount__lte=filter_form.cleaned_data['max_amount'])
            )
        if filter_form.cleaned_data.get('search_description'):
            transactions = transactions.filter(description__icontains=filter_form.cleaned_data['search_description'])
    
    paginator = Paginator(transactions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'transactions': page_obj,
        'filter_form': filter_form,
        'is_paginated': page_obj.paginator.num_pages > 1,
    }
    return render(request, 'bank_statement/transaction_list.html', context)


@login_required
def transaction_delete(request, pk):
    """Delete a transaction"""
    transaction = get_object_or_404(Transaction, pk=pk, statement__user=request.user)
    statement_pk = transaction.statement.pk
    
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Transaction deleted successfully.')
        return redirect('bank_statement:statement_detail', pk=statement_pk)
    
    return render(request, 'bank_statement/transaction_confirm_delete.html', {
        'transaction': transaction
    })


@login_required
def export_all_transactions(request):
    """Export all transactions across user's statements, respecting filters via GET and format param."""
    fmt = (request.GET.get('format') or 'csv').lower()
    valid_formats = {'csv', 'excel', 'json'}
    if fmt not in valid_formats:
        return JsonResponse({'error': 'Invalid format'}, status=400)

    # Base queryset
    transactions = Transaction.objects.filter(statement__user=request.user).order_by('transaction_date')

    # Apply filters using the same logic as transaction_list
    filter_form = TransactionFilterForm(request.GET)
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('date_from'):
            transactions = transactions.filter(transaction_date__gte=filter_form.cleaned_data['date_from'])
        if filter_form.cleaned_data.get('date_to'):
            transactions = transactions.filter(transaction_date__lte=filter_form.cleaned_data['date_to'])
        if filter_form.cleaned_data.get('transaction_type'):
            if filter_form.cleaned_data['transaction_type'] == 'debit':
                transactions = transactions.filter(debit_amount__isnull=False)
            elif filter_form.cleaned_data['transaction_type'] == 'credit':
                transactions = transactions.filter(credit_amount__isnull=False)
        if filter_form.cleaned_data.get('min_amount'):
            transactions = transactions.filter(
                Q(debit_amount__gte=filter_form.cleaned_data['min_amount']) |
                Q(credit_amount__gte=filter_form.cleaned_data['min_amount'])
            )
        if filter_form.cleaned_data.get('max_amount'):
            transactions = transactions.filter(
                Q(debit_amount__lte=filter_form.cleaned_data['max_amount']) |
                Q(credit_amount__lte=filter_form.cleaned_data['max_amount'])
            )
        if filter_form.cleaned_data.get('search_description'):
            transactions = transactions.filter(description__icontains=filter_form.cleaned_data['search_description'])

    # Determine fields to include
    default_fields = ['date', 'description', 'debit', 'credit', 'balance', 'confidence']
    fields_param = request.GET.get('fields')
    if fields_param:
        requested = [f.strip() for f in fields_param.split(',')]
        fields = [f for f in requested if f in default_fields] or default_fields
    else:
        fields = default_fields

    if fmt == 'csv':
        return export_all_csv(transactions, fields)
    elif fmt == 'excel':
        return export_all_excel(transactions, fields)
    else:
        return export_all_json(transactions, fields)


def export_all_csv(transactions, fields):
    """Export all filtered transactions to CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="all_transactions_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)

    # Header
    header = []
    if 'date' in fields:
        header.append('Date')
    if 'description' in fields:
        header.append('Description')
    if 'debit' in fields:
        header.append('Debit Amount')
    if 'credit' in fields:
        header.append('Credit Amount')
    if 'balance' in fields:
        header.append('Balance')
    if 'confidence' in fields:
        header.append('Confidence Score')
    writer.writerow(header)

    # Rows
    for transaction in transactions:
        row = []
        if 'date' in fields:
            row.append(transaction.transaction_date.strftime('%Y-%m-%d'))
        if 'description' in fields:
            row.append(transaction.description)
        if 'debit' in fields:
            row.append(str(transaction.debit_amount) if transaction.debit_amount else '')
        if 'credit' in fields:
            row.append(str(transaction.credit_amount) if transaction.credit_amount else '')
        if 'balance' in fields:
            row.append(str(transaction.balance) if transaction.balance else '')
        if 'confidence' in fields:
            row.append(f"{transaction.confidence_score:.2f}")
        writer.writerow(row)

    return response


def export_all_excel(transactions, fields):
    """Export all filtered transactions to Excel."""
    try:
        import openpyxl
        import pandas as pd
    except ImportError:
        return JsonResponse({'error': 'Excel export not available'}, status=400)

    data = []
    for transaction in transactions:
        row = {}
        if 'date' in fields:
            row['Date'] = transaction.transaction_date
        if 'description' in fields:
            row['Description'] = transaction.description
        if 'debit' in fields:
            row['Debit Amount'] = transaction.debit_amount
        if 'credit' in fields:
            row['Credit Amount'] = transaction.credit_amount
        if 'balance' in fields:
            row['Balance'] = transaction.balance
        if 'confidence' in fields:
            row['Confidence Score'] = transaction.confidence_score
        data.append(row)

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Transactions', index=False)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="all_transactions_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    return response


def export_all_json(transactions, fields):
    """Export all filtered transactions to JSON."""
    data = []
    for transaction in transactions:
        row = {}
        if 'date' in fields:
            row['date'] = transaction.transaction_date.isoformat()
        if 'description' in fields:
            row['description'] = transaction.description
        if 'debit' in fields:
            row['debit_amount'] = str(transaction.debit_amount) if transaction.debit_amount else None
        if 'credit' in fields:
            row['credit_amount'] = str(transaction.credit_amount) if transaction.credit_amount else None
        if 'balance' in fields:
            row['balance'] = str(transaction.balance) if transaction.balance else None
        if 'confidence' in fields:
            row['confidence_score'] = float(transaction.confidence_score)
        data.append(row)

    response = JsonResponse({
        'exported_at': timezone.now().isoformat(),
        'transactions': data
    }, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="all_transactions_{timezone.now().strftime("%Y%m%d")}.json"'
    return response


@login_required
def export_data(request, pk):
    """Export statement data (per-statement) via POST form"""
    statement = get_object_or_404(Statement, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = ExportForm(request.POST)
        if form.is_valid():
            export_format = form.cleaned_data['format']
            include_fields = form.cleaned_data['fields']
            
            transactions = statement.transactions.all().order_by('transaction_date')
            
            if export_format == 'csv':
                return export_csv(transactions, include_fields, statement)
            elif export_format == 'excel':
                return export_excel(transactions, include_fields, statement)
            elif export_format == 'json':
                return export_json(transactions, include_fields, statement)
    else:
        form = ExportForm()
    
    return render(request, 'bank_statement/export_data.html', {
        'form': form,
        'statement': statement
    })


def export_csv(transactions, fields, statement):
    """Export a single statement's transactions to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{statement.bank_name}_{statement.statement_period}_transactions.csv"'
    
    writer = csv.writer(response)
    header = []
    if 'date' in fields:
        header.append('Date')
    if 'description' in fields:
        header.append('Description')
    if 'debit' in fields:
        header.append('Debit Amount')
    if 'credit' in fields:
        header.append('Credit Amount')
    if 'balance' in fields:
        header.append('Balance')
    if 'confidence' in fields:
        header.append('Confidence Score')
    writer.writerow(header)
    
    for transaction in transactions:
        row = []
        if 'date' in fields:
            row.append(transaction.transaction_date.strftime('%Y-%m-%d'))
        if 'description' in fields:
            row.append(transaction.description)
        if 'debit' in fields:
            row.append(str(transaction.debit_amount) if transaction.debit_amount else '')
        if 'credit' in fields:
            row.append(str(transaction.credit_amount) if transaction.credit_amount else '')
        if 'balance' in fields:
            row.append(str(transaction.balance) if transaction.balance else '')
        if 'confidence' in fields:
            row.append(f"{transaction.confidence_score:.2f}")
        writer.writerow(row)
    return response


def export_excel(transactions, fields, statement):
    """Export a single statement's transactions to Excel"""
    try:
        import openpyxl
        import pandas as pd
    except ImportError:
        return JsonResponse({'error': 'Excel export not available'}, status=400)
    
    data = []
    for transaction in transactions:
        row = {}
        if 'date' in fields:
            row['Date'] = transaction.transaction_date
        if 'description' in fields:
            row['Description'] = transaction.description
        if 'debit' in fields:
            row['Debit Amount'] = transaction.debit_amount
        if 'credit' in fields:
            row['Credit Amount'] = transaction.credit_amount
        if 'balance' in fields:
            row['Balance'] = transaction.balance
        if 'confidence' in fields:
            row['Confidence Score'] = transaction.confidence_score
        data.append(row)
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Transactions', index=False)
    output.seek(0)
    
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{statement.bank_name}_{statement.statement_period}_transactions.xlsx"'
    return response


def export_json(transactions, fields, statement):
    """Export a single statement's transactions to JSON"""
    data = []
    for transaction in transactions:
        row = {}
        if 'date' in fields:
            row['date'] = transaction.transaction_date.isoformat()
        if 'description' in fields:
            row['description'] = transaction.description
        if 'debit' in fields:
            row['debit_amount'] = str(transaction.debit_amount) if transaction.debit_amount else None
        if 'credit' in fields:
            row['credit_amount'] = str(transaction.credit_amount) if transaction.credit_amount else None
        if 'balance' in fields:
            row['balance'] = str(transaction.balance) if transaction.balance else None
        if 'confidence' in fields:
            row['confidence_score'] = float(transaction.confidence_score)
        data.append(row)
    
    response = JsonResponse({
        'statement': {
            'bank_name': statement.bank_name,
            'statement_period': statement.statement_period,
            'upload_date': statement.upload_date.isoformat(),
        },
        'transactions': data
    }, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="{statement.bank_name}_{statement.statement_period}_transactions.json"'
    return response


@login_required
@require_http_methods(["POST"])
def reprocess_statement(request, pk):
    """Reprocess a statement"""
    statement = get_object_or_404(Statement, pk=pk, user=request.user)
    
    try:
        # Delete existing transactions
        statement.transactions.all().delete()
        
        # Reset statement status
        statement.processing_status = 'processing'
        statement.processing_completed_at = None
        statement.save()
        
        # Process again
        if getattr(settings, 'USE_CELERY', False):
            from .tasks import process_statement_task
            process_statement_task.delay(statement.id)
            messages.success(request, 'Statement queued for reprocessing.')
        else:
            success, message = process_statement_sync(statement)
            if success:
                messages.success(request, f'Reprocessing completed: {message}')
            else:
                messages.error(request, f'Reprocessing failed: {message}')
        
    except Exception as e:
        logger.error(f"Reprocessing failed for statement {statement.id}: {str(e)}")
        messages.error(request, f'Reprocessing failed: {str(e)}')
    
    return redirect('bank_statement:statement_detail', pk=pk)


@login_required
def ajax_transaction_search(request):
    """AJAX endpoint for transaction search"""
    query = request.GET.get('q', '')
    statement_id = request.GET.get('statement_id')
    
    if not query or len(query) < 3:
        return JsonResponse({'results': []})
    
    transactions = Transaction.objects.filter(
        statement__user=request.user,
        description__icontains=query
    )
    
    if statement_id:
        transactions = transactions.filter(statement_id=statement_id)
    
    transactions = transactions[:10]  # Limit results
    
    results = []
    for transaction in transactions:
        results.append({
            'id': transaction.id,
            'date': transaction.transaction_date.strftime('%Y-%m-%d'),
            'description': transaction.description,
            'amount': str(transaction.debit_amount or transaction.credit_amount or ''),
            'type': 'debit' if transaction.debit_amount else 'credit'
        })
    
    return JsonResponse({'results': results})


@login_required
def processing_status(request, pk):
    """Get processing status for a statement"""
    statement = get_object_or_404(Statement, pk=pk, user=request.user)
    
    return JsonResponse({
        'status': statement.processing_status,
        'processed_at': statement.processing_completed_at.isoformat() if statement.processing_completed_at else None,
        'transaction_count': statement.transactions.count(),
        'logs': [
            {
                'level': log.level,
                'message': log.message,
                'created_at': log.timestamp.isoformat()
            }
            for log in statement.processing_logs.order_by('-timestamp')[:5]
        ]
    })
