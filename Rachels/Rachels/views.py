from django.http import HttpResponse
from .forms import RecordForm
from django.core.paginator import Paginator
from .models import Record
from datetime import datetime, date
from django.db.models import Count, Q
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages
import csv

def show_all_records(request):
    """
    Display the records list with:
      - search (q -> details__icontains)
      - filters: location, status
      - quick toggle: ?month=this  (filters to current month)
      - pagination (page param)
      - pagination_items: list containing page numbers and '...' for template
    """

    qs = Record.objects.all().order_by('-date', '-id')

    # --- Filters from query params ---
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(details__icontains=q)

    location = request.GET.get('location', '').strip()
    if location:
        qs = qs.filter(location=location)

    status = request.GET.get('status', '').strip()
    if status:
        qs = qs.filter(status__iexact=status)

    # Quick "This Month" filter
    if request.GET.get('month') == 'this':
        today = date.today()
        qs = qs.filter(date__year=today.year, date__month=today.month)

    # --- Pagination ---
    per_page = 25
    paginator = Paginator(qs, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Build pagination_items list (ints and '...')
    total_pages = paginator.num_pages
    current = page_obj.number if page_obj else 1
    pagination_items = []
    last_was_ellipsis = False

    for p in range(1, total_pages + 1):
        show = (
            p <= 2 or                     # first two pages
            p > total_pages - 2 or        # last two pages
            abs(p - current) <= 1         # neighbors of current
        )
        if show:
            pagination_items.append(p)
            last_was_ellipsis = False
        else:
            if not last_was_ellipsis:
                pagination_items.append('...')
                last_was_ellipsis = True

    context = {
        # iterate over "records" in template
        'records': page_obj.object_list,
        # paginator info for page controls
        'page_obj': page_obj,
        'paginator': paginator,
        # precomputed list for template rendering (contains ints and '...')
        'pagination_items': pagination_items,
        # include request so template can read request.GET easily
        'request': request,
    }

    return render(request, 'DisplayRecord.html', context)


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

def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None

def export_form(request):
    initial = {
        'from_date': request.GET.get('from_date', ''),
        'to_date': request.GET.get('to_date', ''),
        'location': request.GET.get('location', ''),
        'status': request.GET.get('status', ''),
    }
    return render(request, "export_records.html", {'initial': initial})


def export_csv(request):
    # Accept both GET and POST
    data = request.GET if request.method == "GET" else request.POST

    from_date = _parse_date(data.get('from_date', '').strip())
    to_date = _parse_date(data.get('to_date', '').strip())
    location = data.get('location', '').strip()
    status = data.get('status', '').strip()

    # Basic validation
    if from_date and to_date and from_date > to_date:
        # If called via POST, redirect back with a message. If GET, render form with message.
        messages.error(request, "From date cannot be after To date.")
        return redirect('export_form')

    qs = Record.objects.all().order_by('date', 'id')

    if from_date:
        qs = qs.filter(date__gte=from_date)
    if to_date:
        qs = qs.filter(date__lte=to_date)
    if location:
        qs = qs.filter(location=location)
    if status:
        qs = qs.filter(status__iexact=status)

    # Build filename using provided dates (fall back to today if missing)
    fd = from_date.isoformat() if from_date else timezone.localdate().isoformat()
    td = to_date.isoformat() if to_date else timezone.localdate().isoformat()

    filename = f"orders-{fd}-{td}.csv"

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    # header row - adjust columns as needed
    writer.writerow(['ID', 'Date', 'Location', 'Status', 'Details'])

    for r in qs:
        # Ensure strings don't break CSV (writer handles quoting)
        writer.writerow([r.pk, r.date.isoformat(), r.location, r.status, r.details])

    return response
