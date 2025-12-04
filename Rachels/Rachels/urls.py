from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name = 'Home'),
    path('add/', views.add_record, name='add_record'),
    path('records/', views.show_all_records, name='show_all_records'),
    path('record/<int:pk>/delete/', views.delete_record, name='delete_record'),
    path('record/<int:pk>/', views.record_detail, name='record_detail'),
    path('record/<int:pk>/complete/', views.mark_completed, name='mark_completed'),
    path('export/', views.export_form, name='export_form'),
    path('export/csv/', views.export_csv, name='export_csv'),
]
