from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import *

urlpatterns = [
    path('admin/', admin.site.urls),

    # AUTH
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', logout_view, name='logout'),

    # MAIN
    path('', home, name='Home'),
    path('add/', add_record, name='add_record'),
    path('records/', show_all_records, name='show_all_records'),
    path('record/<int:pk>/delete/', delete_record, name='delete_record'),
    path('record/<int:pk>/', record_detail, name='record_detail'),
    path('record/<int:pk>/complete/', mark_completed, name='mark_completed'),

    path('export/', export_form, name='export_form'),
    path("export/excel/", export_excel, name="export_excel"),

    path('vendors/add/', add_vendor, name='add_vendor'),

    # ADVANCES (admin only)
    path("advances/", advance_list, name="advance_list"),
    path("advances/add/", advance_add, name="advance_add"),
    path("advances/<int:pk>/delete/", advance_delete, name="advance_delete"),
    path("advance-salary/", advance_list, name="advance_salary_home"),
    path("records/<int:pk>/edit/", edit_order, name="edit_order"),
    path("notifications/", fetch_notifications, name="fetch_notifications"),
    path("notifications/clear/", clear_notifications, name="clear_notifications"),
    path("notifications/read/<int:pk>/", mark_notification_read, name="mark_notification_read"),
    path("inventory/", inventory_overview, name="inventory_overview"),
    path("stores/", manage_stores, name="manage_stores"),
]
