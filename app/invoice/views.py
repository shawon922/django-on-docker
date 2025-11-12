from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction as db_transaction

from .models import Invoice, InvoiceLine
from .forms import InvoiceUploadForm
from .utils import POSReceiptProcessor


@login_required
def upload_receipt(request):
    if request.method == 'POST':
        form = InvoiceUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with db_transaction.atomic():
                    # 1️⃣ Save initial invoice entry (file upload only)
                    inv = form.save(commit=False)
                    inv.user = request.user
                    inv.save()

                    # 2️⃣ Extract + Parse receipt text
                    processor = POSReceiptProcessor(inv)
                    parsed = processor.process()

                    # 3️⃣ Prepare data ready for DB models
                    prepared = processor.prepare_invoice_data(parsed)
                    invoice_data = prepared['invoice']
                    lines_data = prepared['lines']

                    # 4️⃣ Update invoice fields
                    for field, value in invoice_data.items():
                        setattr(inv, field, value)
                    inv.save()

                    # 5️⃣ Replace old lines with parsed ones
                    inv.lines.all().delete()
                    InvoiceLine.objects.bulk_create([
                        InvoiceLine(invoice=inv, **line) for line in lines_data
                    ])

                    # 6️⃣ Notify success
                    messages.success(request, 'Receipt uploaded and parsed successfully.')
                    return redirect('invoice:detail', pk=inv.pk)

            except Exception as e:
                messages.error(request, f'Failed to process receipt: {e}')
    else:
        form = InvoiceUploadForm()

    return render(request, 'invoice/upload.html', {'form': form})


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, user=request.user)
    return render(request, 'invoice/detail.html', {'invoice': invoice})


@login_required
def invoice_list(request):
    invoices = Invoice.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'invoice/list.html', {'invoices': invoices})
