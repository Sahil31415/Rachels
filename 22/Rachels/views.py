from django.http import HttpResponse
from .forms import RecordForm
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from .models import Record
from datetime import datetime
from django.db.models import Count, Q

def show_all_records(request):
    records = Record.objects.all().order_by('-date')   # newest first
    return render(request, "DisplayRecord.html", {"records": records})

def add_record(request):
    if request.method == "POST":
        form = RecordForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/')
    else:
        form = RecordForm()

    return render(request, "addRecord.html", {"form": form})
# ... other imports you already have

def home(request):
    # Determine if there's a status field in the model
    field_names = [f.name for f in Record._meta.fields]
    has_status = 'status' in field_names

    # Total pending (if status exists) or all records fallback
    if has_status:
        total_pending = Record.objects.filter(status__iexact='Pending').count()
    else:
        total_pending = Record.objects.count()

    # Pending by location summary (counts)
    if has_status:
        pending_by_location_qs = (
            Record.objects
                  .filter(status__iexact='Pending')
                  .values('location')
                  .annotate(count=Count('id'))
                  .order_by('-count', 'location')
        )
    else:
        pending_by_location_qs = (
            Record.objects
                  .values('location')
                  .annotate(count=Count('id'))
                  .order_by('-count', 'location')
        )
    pending_by_location = list(pending_by_location_qs)

    # Top 5 orders:
    # If we have 'status' treat top 5 as latest pending; otherwise simply latest 5 records
    if has_status:
        top5_orders = Record.objects.filter(status__iexact='Pending').order_by('-date', '-id')[:5]
    else:
        top5_orders = Record.objects.all().order_by('-date', '-id')[:5]

    # Latest 5 records for quick glance (kept for backward compatibility / other UI use)
    latest_records = Record.objects.all().order_by('-date', '-id')[:5]

    # Build three location cards. Use same choices you defined in form.
    LOCATIONS = ['Dulari', 'Pours and Plates', 'Rachels']
    location_cards = []
    for loc in LOCATIONS:
        if has_status:
            pending_qs = Record.objects.filter(location=loc, status__iexact='Pending').order_by('-date', '-id')
            # treat any non-pending as successful/other; adjust condition if you have specific success terms
            successful_qs = Record.objects.filter(location=loc).exclude(status__iexact='Pending').order_by('-date', '-id')
        else:
            # if no status field, treat all records as 'pending' per your earlier fallback
            pending_qs = Record.objects.filter(location=loc).order_by('-date', '-id')
            successful_qs = Record.objects.none()

        location_cards.append({
            'location': loc,
            'pending': list(pending_qs),
            'successful': list(successful_qs),
            'pending_count': pending_qs.count(),
            'successful_count': successful_qs.count(),
        })

    context = {
        'total_pending': total_pending,
        'pending_by_location': pending_by_location,
        'latest_records': latest_records,
        'top5_orders': top5_orders,
        'location_cards': location_cards,
    }
    return render(request, "home.html", context)

def delete_record(request, pk):
    record = get_object_or_404(Record, pk=pk)

    if request.method == "POST":
        record.delete()
        return redirect('show_all_records')   # redirect back to all records

    return render(request, "delete_record.html", {"record": record})

from django.shortcuts import render, get_object_or_404
from .models import Record

def record_detail(request, pk):
    """
    Show full details for a single Record.
    """
    record = get_object_or_404(Record, pk=pk)
    return render(request, "record_detail.html", {"record": record})

def mark_completed(request, pk):
    record = get_object_or_404(Record, pk=pk)

    # Only allow POST to avoid accidental status changes
    if request.method == "POST":
        record.status = "Completed"
        record.save()
        return redirect('show_all_records')

    # fallback redirect
    return redirect('record_detail', pk=pk)