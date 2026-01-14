# views.py
from datetime import datetime, date
import csv
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Sum
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.core.paginator import Paginator
from .forms import AdvanceSalaryForm, RecordForm, VendorForm
from .models import AdvanceSalary, Record, Vendor, VendorItem
from decimal import Decimal
from django.http import JsonResponse
from .models import Notification
from django.contrib.auth import get_user_model
from collections import defaultdict
import openpyxl
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter
from django.db.models import Max, Q

User = get_user_model()

def _normalize_location_for_group(loc):
    if not loc:
        return ""
    return ''.join(ch.lower() if ch.isalnum() else '_' for ch in loc).strip('_')

def user_is_admin(user):
    return user.is_authenticated and user.is_superuser

def user_in_manager_group_for_location(user, location):
    if not user.is_authenticated:
        return False
    grp_name = f"manager_{_normalize_location_for_group(location)}"
    return user.groups.filter(name=grp_name).exists()

def user_can_view_location(user, record_location):
    # Superuser: full access
    if user.is_superuser:
        return True

    # Manager: only their assigned location
    if hasattr(user, "managerprofile"):
        return user.managerprofile.location == record_location

    # Default: no access
    return False

def admin_required(view_func):
    return user_passes_test(user_is_admin)(view_func)

@login_required
def home(request):
    field_names = [f.name for f in Record._meta.fields]
    has_status = 'status' in field_names
    if has_status:
        total_pending = Record.objects.filter(status__iexact='Pending').count()
    else:
        total_pending = Record.objects.count()

    if has_status:
        pending_by_location = list(
            Record.objects
                  .filter(status__iexact='Pending')
                  .values('location')
                  .annotate(count=Count('id'))
                  .order_by('-count', 'location')
        )
    else:
        pending_by_location = list(
            Record.objects
                  .values('location')
                  .annotate(count=Count('id'))
                  .order_by('-count', 'location')
        )

    if has_status:
        top5_orders = (
            Record.objects
                  .filter(status__iexact='Pending')
                  .order_by('-date', '-id')[:5]
        )
    else:
        top5_orders = Record.objects.order_by('-date', '-id')[:5]

    latest_records = Record.objects.order_by('-date', '-id')[:5]

    ALL_LOCATIONS = ['Dulari', 'Pours and Plates', 'Rachels', 'Rachels1', 'Rachels2']
    location_cards = []

    for loc in ALL_LOCATIONS:
        if not user_can_view_location(request.user, loc):
            continue

        if has_status:
            pending_base = Record.objects.filter(
                location=loc,
                status__iexact='Pending'
            ).order_by('-date', '-id')

            successful_base = Record.objects.filter(
                location=loc
            ).exclude(
                status__iexact='Pending'
            ).order_by('-date', '-id')
        else:
            pending_base = Record.objects.filter(location=loc).order_by('-date', '-id')
            successful_base = Record.objects.none()

        location_cards.append({
            "location": loc,
            "pending": list(pending_base[:5]),
            "successful": list(successful_base[:5]),
            "pending_count": pending_base.count(),
            "successful_count": successful_base.count(),
        })

    context = {
        "total_pending": total_pending,
        "pending_by_location": pending_by_location,
        "latest_records": latest_records,
        "top5_orders": top5_orders,
        "location_cards": location_cards,
    }
    return render(request, "home.html", context)

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

@login_required
def record_detail(request, pk):
    record = get_object_or_404(Record, pk=pk)

    if not user_can_view_location(request.user, record.location):
        return HttpResponseForbidden("You don't have permission to view this record.")

    # Safe total calculation
    total_amount = 0
    if record.item and record.item.unit_price:
        total_amount = record.quantity * record.item.unit_price

    context = {
        "record": record,
        "total_amount": total_amount,
        "is_admin": request.user.is_superuser,
    }

    return render(request, "record_detail.html", context)

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

def export_excel(request):
    data = request.GET if request.method == "GET" else request.POST

    from_date = _parse_date(data.get('from_date', '').strip())
    to_date = _parse_date(data.get('to_date', '').strip())
    location = data.get('location', '').strip()
    status = data.get('status', '').strip()

    if from_date and to_date and from_date > to_date:
        messages.error(request, "From date cannot be after To date.")
        return redirect('export_form')

    qs = Record.objects.select_related(
        'vendor', 'item'
    ).order_by('-date', '-id')  # recent first

    if from_date:
        qs = qs.filter(date__gte=from_date)
    if to_date:
        qs = qs.filter(date__lte=to_date)
    if location:
        qs = qs.filter(location=location)
    if status:
        qs = qs.filter(status__iexact=status)

    # ---------- GROUP DATA ----------
    # location -> vendor -> item -> [records]
    grouped = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )

    for r in qs:
        loc = r.location or "Unknown"
        vendor = r.vendor.name if r.vendor else "Unknown Vendor"
        item = r.item.item_name if r.item else "Unknown Item"
        grouped[loc][vendor][item].append(r)

    # ---------- CREATE EXCEL ----------
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default sheet

    header = ['Order ID', 'Date', 'Status', 'Quantity']
    header_font = Font(bold=True)

    for loc, vendors in grouped.items():
        ws = wb.create_sheet(title=loc[:31])  # Excel sheet name limit

        row = 1
        ws.cell(row=row, column=1, value=f"Location: {loc}")
        ws.cell(row=row, column=1).font = Font(bold=True, size=14)
        row += 2

        for vendor, items in vendors.items():
            ws.cell(row=row, column=1, value=f"Vendor: {vendor}")
            ws.cell(row=row, column=1).font = Font(bold=True)
            row += 1

            for item, records in items.items():
                ws.cell(row=row, column=1, value=f"Item: {item}")
                ws.cell(row=row, column=1).font = Font(italic=True)
                row += 1

                # table header
                for col, h in enumerate(header, start=1):
                    cell = ws.cell(row=row, column=col, value=h)
                    cell.font = header_font
                row += 1

                for r in records:
                    ws.append([
                        r.pk,
                        r.date.isoformat() if r.date else '',
                        r.status,
                        r.quantity,
                    ])
                    row += 1

                row += 1  # space after item

            row += 1  # space after vendor

        # autosize columns
        for col in ws.columns:
            ws.column_dimensions[get_column_letter(col[0].column)].width = 20

    fd = from_date.isoformat() if from_date else timezone.localdate().isoformat()
    td = to_date.isoformat() if to_date else timezone.localdate().isoformat()

    filename = f"orders-{fd}-{td}.xlsx"

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    wb.save(response)
    return response

@login_required
def add_vendor(request):
    if request.method == "POST":
        form = VendorForm(request.POST)

        items = request.POST.getlist("items[]")
        units = request.POST.getlist("units[]")
        prices = request.POST.getlist("prices[]")

        if form.is_valid() and items:
            vendor = form.save()

            for name, unit, price in zip(items, units, prices):
                if name.strip() and unit and price:
                    VendorItem.objects.create(
                        vendor=vendor,
                        item_name=name.strip(),
                        unit=unit,
                        unit_price=price
                    )

            messages.success(request, "Vendor and items saved successfully.")
            return redirect("Home")

        messages.error(request, "Please provide vendor name and valid items.")

    else:
        form = VendorForm()

    return render(request, "add_vendor.html", {"form": form})

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

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')

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

    if not is_admin and not manager_location:
        return HttpResponseForbidden("You are not allowed to add records.")

    if request.method == "POST":
        date = request.POST.get("date")

        if is_admin:
            location = request.POST.get("location")
        else:
            location = manager_location

        vendors = request.POST.getlist("vendor[]")
        items = request.POST.getlist("item[]")
        quantities = request.POST.getlist("quantity[]")

        for v, i, q in zip(vendors, items, quantities):
            if v and i and q:
                record = Record.objects.create(
                    date=date,
                    location=location,
                    vendor_id=v,
                    item_id=i,
                    quantity=q,
                    status="Pending",
                )
                admins = User.objects.filter(is_superuser=True)

                print(record.pk)
                
                for admin in admins:
                    Notification.objects.create(
                        recipient=admin,
                        message=f"New order added (#{record.pk})",
                        location=record.location,
                        url=reverse("record_detail", kwargs={"pk": record.pk}),
                    )

        return redirect("show_all_records")

    vendors = Vendor.objects.prefetch_related("items")
    form = RecordForm()

    context = {
        "form": form,
        "vendors": vendors,
        "is_admin": is_admin,
        "manager_location": manager_location,
    }
    return render(request, "addRecord.html", context)

@login_required
def edit_order(request, pk):
    record = get_object_or_404(Record, pk=pk)

    if not request.user.is_staff:
        return redirect("record_detail", pk=pk)

    if request.method == "POST":
        record.quantity = int(request.POST["quantity"])
        record.item.unit_price = Decimal(request.POST["unit_price"])

        record.item.save()
        record.save()

        managers = User.objects.filter(
            managerprofile__location=record.location
        )

        for manager in managers:
            Notification.objects.create(
                recipient=manager,
                message=f"Order #{record.pk} was updated",
                location=record.location,
                url=reverse("record_detail", kwargs={"pk": record.pk}),
            )

    return redirect("record_detail", pk=pk)

@login_required
def fetch_notifications(request):
    user = request.user

    # Group notifications by location
    grouped = (
        user.notifications
        .values("location")
        .annotate(
            latest_time=Max("created_at"),
            unread_count=Count("id", filter=Q(is_read=False))
        )
        .order_by("-latest_time")
    )

    data = []

    for g in grouped:
        data.append({
            "location": g["location"],
            "has_unread": g["unread_count"] > 0,
            "latest_time": g["latest_time"].strftime("%d %b, %H:%M"),
        })

    total_unread_locations = sum(1 for g in grouped if g["unread_count"] > 0)

    return JsonResponse({
        "notifications": data,
        "unread_count": total_unread_locations
    })

@login_required
def clear_notifications(request):
    request.user.notifications.all().delete()
    return JsonResponse({"status": "ok"})

@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user
    )
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return JsonResponse({"ok": True})

def inventory_overview(request):
    qs = (
        Record.objects
        .filter(
            status="Completed",
            item__isnull=False
        )
        .values(
            "location",
            "item__item_name"
        )
        .annotate(total_quantity=Sum("quantity"))
        .order_by("location", "item__item_name")
    )

    inventory_by_store = defaultdict(list)

    for row in qs:
        inventory_by_store[row["location"]].append(row)

    return render(request, "inventory_overview.html", {
        "inventory_by_store": dict(inventory_by_store)
    })