# views.py
from datetime import datetime, date
import csv

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.paginator import Paginator

from .forms import AdvanceSalaryForm, RecordForm, VendorForm
from .models import AdvanceSalary, Record, Vendor, VendorItem


# ------------------------
# Helper utilities
# ------------------------
def _normalize_location_for_group(loc):
    """
    Normalizes a location string to a group fragment.
    e.g. "Pours and Plates" -> "pours_and_plates"
    """
    if not loc:
        return ""
    return ''.join(ch.lower() if ch.isalnum() else '_' for ch in loc).strip('_')


def user_is_admin(user):
    return user.is_authenticated and user.is_superuser


def user_in_manager_group_for_location(user, location):
    """
    Returns True when the user belongs to a group named
    manager_<normalized_location>.
    e.g. manager_dulari, manager_pours_and_plates, manager_rachels1
    """
    if not user.is_authenticated:
        return False
    grp_name = f"manager_{_normalize_location_for_group(location)}"
    return user.groups.filter(name=grp_name).exists()


def user_can_view_location(user, location):
    """
    Admin sees everything. Managers see only their assigned location.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user_in_manager_group_for_location(user, location)


def admin_required(view_func):
    """ Shortcut decorator for admin-only views """
    return user_passes_test(user_is_admin)(view_func)


# ------------------------
# Dashboard / Home
# ------------------------
@login_required
def home(request):
    """
    Dashboard — show totals, top orders and per-location cards.
    Managers will only see the locations they are allowed to; admin sees all.
    """
    # detect whether model has a 'status' field
    field_names = [f.name for f in Record._meta.fields]
    has_status = 'status' in field_names

    # total pending
    if has_status:
        total_pending = Record.objects.filter(status__iexact='Pending').count()
    else:
        total_pending = Record.objects.count()

    # pending by location
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

    # top 5 orders
    if has_status:
        top5_orders = Record.objects.filter(status__iexact='Pending').order_by('-date', '-id')[:5]
    else:
        top5_orders = Record.objects.all().order_by('-date', '-id')[:5]

    latest_records = Record.objects.all().order_by('-date', '-id')[:5]

    # Locations to build cards for — sync with your choices/form
    ALL_LOCATIONS = ['Dulari', 'Pours and Plates', 'Rachels', 'Rachels1', 'Rachels2']
    location_cards = []
    for loc in ALL_LOCATIONS:
        # if user not allowed to view this location, skip
        if not user_can_view_location(request.user, loc):
            continue

        if has_status:
            pending_qs = Record.objects.filter(location=loc, status__iexact='Pending').order_by('-date', '-id')
            successful_qs = Record.objects.filter(location=loc).exclude(status__iexact='Pending').order_by('-date', '-id')
        else:
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


# ------------------------
# All records listing (with filters + pagination)
# ------------------------
@login_required
def show_all_records(request):
    qs = Record.objects.all().order_by('-date', '-id')

    # text search (your model previously referenced "details" — if absent remove this)
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(details__icontains=q)

    location = request.GET.get('location', '').strip()
    if location:
        qs = qs.filter(location=location)

    status = request.GET.get('status', '').strip()
    if status:
        qs = qs.filter(status__iexact=status)

    if request.GET.get('month') == 'this':
        today = date.today()
        qs = qs.filter(date__year=today.year, date__month=today.month)

    # Pagination
    per_page = 25
    paginator = Paginator(qs, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # compact pagination list
    total_pages = paginator.num_pages
    current = page_obj.number if page_obj else 1
    pagination_items = []
    last_was_ellipsis = False
    for p in range(1, total_pages + 1):
        show = (
            p <= 2 or
            p > total_pages - 2 or
            abs(p - current) <= 1
        )
        if show:
            pagination_items.append(p)
            last_was_ellipsis = False
        else:
            if not last_was_ellipsis:
                pagination_items.append('...')
                last_was_ellipsis = True

    context = {
        'records': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'pagination_items': pagination_items,
        'request': request,
    }
    return render(request, 'DisplayRecord.html', context)

# ------------------------
# Record detail + admin actions
# ------------------------
@login_required
def record_detail(request, pk):
    record = get_object_or_404(Record, pk=pk)
    if not user_can_view_location(request.user, record.location):
        return HttpResponseForbidden("You don't have permission to view this record.")
    return render(request, "record_detail.html", {"record": record})


@admin_required
def mark_completed(request, pk):
    record = get_object_or_404(Record, pk=pk)
    if request.method == "POST":
        record.status = "Completed"
        record.save()
        messages.success(request, "Record marked completed.")
        return redirect('show_all_records')
    return redirect('record_detail', pk=pk)


@admin_required
def delete_record(request, pk):
    record = get_object_or_404(Record, pk=pk)
    if request.method == "POST":
        record.delete()
        messages.success(request, "Record deleted.")
        return redirect('show_all_records')
    return render(request, "delete_record.html", {"record": record})


# ------------------------
# CSV export
# ------------------------
def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


@login_required
def export_form(request):
    initial = {
        'from_date': request.GET.get('from_date', ''),
        'to_date': request.GET.get('to_date', ''),
        'location': request.GET.get('location', ''),
        'status': request.GET.get('status', ''),
    }
    return render(request, "export_records.html", {'initial': initial})


@login_required
def export_csv(request):
    data = request.GET if request.method == "GET" else request.POST
    from_date = _parse_date(data.get('from_date', '').strip())
    to_date = _parse_date(data.get('to_date', '').strip())
    location = data.get('location', '').strip()
    status = data.get('status', '').strip()

    if from_date and to_date and from_date > to_date:
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

    fd = from_date.isoformat() if from_date else timezone.localdate().isoformat()
    td = to_date.isoformat() if to_date else timezone.localdate().isoformat()
    filename = f"orders-{fd}-{td}.csv"

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Date', 'Location', 'Status', 'Vendor', 'Item', 'Quantity'])
    for r in qs:
        writer.writerow([
            r.pk,
            r.date.isoformat() if r.date else '',
            r.location,
            r.status,
            r.vendor.name if r.vendor else '',
            r.item.item_name if r.item else '',
            r.quantity,
        ])
    return response


# ------------------------
# Vendor management
# ------------------------
@login_required
def add_vendor(request):
    """
    Add vendor and items. If you want to restrict vendor creation to admin
    only, decorate with @admin_required.
    """
    if request.method == "POST":
        form = VendorForm(request.POST)
        items = request.POST.getlist("items[]")
        if form.is_valid() and items:
            vendor = form.save()
            for item in items:
                if item.strip():
                    VendorItem.objects.create(vendor=vendor, item_name=item.strip())
            messages.success(request, "Vendor saved.")
            return redirect("Home")
        else:
            messages.error(request, "Provide vendor name and at least one item.")
    else:
        form = VendorForm()
    return render(request, "add_vendor.html", {"form": form})


# ------------------------
# Advance salaries (admin only)
# ------------------------
@admin_required
def advance_list(request):
    qs = AdvanceSalary.objects.all()
    total_given = qs.aggregate(total=Sum("amount"))["total"] or 0
    return render(request, "advance_list.html", {
        "advances": qs,
        "total_given": total_given,
    })


@admin_required
def advance_add(request):
    if request.method == "POST":
        form = AdvanceSalaryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Advance saved.")
            return redirect("advance_list")
    else:
        form = AdvanceSalaryForm()
    return render(request, "advance_add.html", {"form": form})


@admin_required
def advance_delete(request, pk):
    adv = get_object_or_404(AdvanceSalary, pk=pk)
    if request.method == "POST":
        adv.delete()
        messages.success(request, "Advance removed.")
        return redirect("advance_list")
    return render(request, "advance_confirm_delete.html", {"advance": adv})


# ------------------------
# Logout
# ------------------------
@login_required
def logout_view(request):
    logout(request)
    return redirect('login')  # or 'Home' depending on your flow

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

# helper you already conceptually have from the login system
def _get_manager_location(user):
    if not user.is_authenticated:
        return None

    if user.is_superuser:
        return None  # admin is not tied to a single location

    # Example mapping by username – tweak as needed
    mapping = {
        "manager_dulari": "Dulari",
        "manager_pnp": "Pours and Plates",
        "manager_rachels": "Rachels",
        "manager_r1": "Rachels1",
        "manager_r2": "Rachels2",
    }
    return mapping.get(user.username)

@login_required
def add_record(request):
    user = request.user
    is_admin = user.is_superuser
    manager_location = _get_manager_location(user)

    # Security: if not admin AND no mapped location, don't allow access
    if not is_admin and not manager_location:
        return HttpResponseForbidden("You are not allowed to add records.")

    if request.method == "POST":
        date = request.POST.get("date")

        if is_admin:
            # Admin may choose any location from form
            location = request.POST.get("location")
        else:
            # Manager: ignore whatever was posted, force their own branch
            location = manager_location

        vendors = request.POST.getlist("vendor[]")
        items = request.POST.getlist("item[]")
        quantities = request.POST.getlist("quantity[]")

        for v, i, q in zip(vendors, items, quantities):
            if v and i and q:
                Record.objects.create(
                    date=date,
                    location=location,
                    vendor_id=v,
                    item_id=i,
                    quantity=q,
                    status="Pending",
                )

        return redirect("Home")

    # GET: build form + vendor list
    vendors = Vendor.objects.prefetch_related("items")
    form = RecordForm()

    context = {
        "form": form,
        "vendors": vendors,
        "is_admin": is_admin,
        "manager_location": manager_location,
    }
    return render(request, "addRecord.html", context)
