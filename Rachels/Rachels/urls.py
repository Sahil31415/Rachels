from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),

    # AUTH
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),

    # MAIN
    path('', views.home, name='Home'),
    path('add/', views.add_record, name='add_record'),
    path('records/', views.show_all_records, name='show_all_records'),
    path('record/<int:pk>/delete/', views.delete_record, name='delete_record'),
    path('record/<int:pk>/', views.record_detail, name='record_detail'),
    path('record/<int:pk>/complete/', views.mark_completed, name='mark_completed'),

    path('export/', views.export_form, name='export_form'),
    path("export/excel/", views.export_excel, name="export_excel"),

    path('vendors/add/', views.add_vendor, name='add_vendor'),

    # ADVANCES (admin only)
    path("advances/", views.advance_list, name="advance_list"),
    path("advances/add/", views.advance_add, name="advance_add"),
    path("advances/<int:pk>/delete/", views.advance_delete, name="advance_delete"),
    path("advance-salary/", views.advance_list, name="advance_salary_home"),
    path("records/<int:pk>/edit/", views.edit_order, name="edit_order"),
    path("notifications/", views.fetch_notifications, name="fetch_notifications"),
    path("notifications/clear/", views.clear_notifications, name="clear_notifications"),
    path("notifications/read/<int:pk>/", views.mark_notification_read, name="mark_notification_read"),
]
