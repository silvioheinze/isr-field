"""
URL configuration for isrfield project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from frontend import views as frontend_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('logout/', frontend_views.logout_view, name='logout'),
    path('password-reset/', frontend_views.password_reset_view, name='password_reset_form'),
    path('password-reset/done/', frontend_views.password_reset_done_view, name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', frontend_views.password_reset_confirm_view, name='password_reset_confirm'),
    path('password-reset-complete/', frontend_views.password_reset_complete_view, name='password_reset_complete'),
    path('register/', frontend_views.register_view, name='register'),
    path('profile/', frontend_views.profile_view, name='profile'),
    path('users/', frontend_views.user_management_view, name='user_management'),
    path('users/create/', frontend_views.create_user_view, name='create_user'),
    path('users/edit/<int:user_id>/', frontend_views.edit_user_view, name='edit_user'),
    path('users/delete/<int:user_id>/', frontend_views.delete_user_view, name='delete_user'),
    path('groups/create/', frontend_views.create_group_view, name='create_group'),
    path('groups/edit/<int:group_id>/', frontend_views.edit_group_view, name='edit_group'),
    path('users/groups/<int:user_id>/', frontend_views.modify_user_groups_view, name='modify_user_groups'),
    path('datasets/', frontend_views.dataset_list_view, name='dataset_list'),
    path('datasets/create/', frontend_views.dataset_create_view, name='dataset_create'),
    path('datasets/<int:dataset_id>/', frontend_views.dataset_detail_view, name='dataset_detail'),
    path('datasets/<int:dataset_id>/edit/', frontend_views.dataset_edit_view, name='dataset_edit'),
    path('datasets/<int:dataset_id>/field-config/', frontend_views.dataset_field_config_view, name='dataset_field_config'),
    path('datasets/<int:dataset_id>/custom-fields/create/', frontend_views.custom_field_create_view, name='custom_field_create'),
    path('datasets/<int:dataset_id>/custom-fields/<int:field_id>/edit/', frontend_views.custom_field_edit_view, name='custom_field_edit'),
    path('datasets/<int:dataset_id>/custom-fields/<int:field_id>/delete/', frontend_views.custom_field_delete_view, name='custom_field_delete'),
    path('datasets/<int:dataset_id>/access/', frontend_views.dataset_access_view, name='dataset_access'),
    path('datasets/<int:dataset_id>/import/', frontend_views.dataset_csv_import_view, name='dataset_csv_import'),
    path('datasets/<int:dataset_id>/import/summary/', frontend_views.import_summary_view, name='import_summary'),
    path('datasets/<int:dataset_id>/debug-import/', frontend_views.debug_import_view, name='debug_import'),
    path('datasets/<int:dataset_id>/export/', frontend_views.dataset_export_options_view, name='dataset_export_options'),
    path('datasets/<int:dataset_id>/export/csv/', frontend_views.dataset_csv_export_view, name='dataset_csv_export'),
    path('datasets/<int:dataset_id>/data-input/', frontend_views.dataset_data_input_view, name='dataset_data_input'),
    path('datasets/<int:dataset_id>/map-data/', frontend_views.dataset_map_data_view, name='dataset_map_data'),
    path('datasets/<int:dataset_id>/clear-data/', frontend_views.dataset_clear_data_view, name='dataset_clear_data'),
    path('datasets/<int:dataset_id>/geometries/create/', frontend_views.geometry_create_view, name='geometry_create'),
    path('entries/<int:entry_id>/edit/', frontend_views.entry_edit_view, name='entry_edit'),
    path('entries/<int:entry_id>/', frontend_views.entry_detail_view, name='entry_detail'),
    path('entries/<int:entry_id>/upload/', frontend_views.file_upload_view, name='file_upload'),
    path('files/<int:file_id>/download/', frontend_views.file_download_view, name='file_download'),
    path('files/<int:file_id>/delete/', frontend_views.file_delete_view, name='file_delete'),
    path('geometries/<int:geometry_id>/entries/create/', frontend_views.entry_create_view, name='entry_create'),
    path('typologies/', frontend_views.typology_list_view, name='typology_list'),
    path('typologies/create/', frontend_views.typology_create_view, name='typology_create'),
    path('typologies/<int:typology_id>/', frontend_views.typology_detail_view, name='typology_detail'),
    path('typologies/<int:typology_id>/edit/', frontend_views.typology_edit_view, name='typology_edit'),
    path('typologies/<int:typology_id>/import/', frontend_views.typology_import_view, name='typology_import'),
    path('typologies/<int:typology_id>/export/', frontend_views.typology_export_view, name='typology_export'),
    path('datasets/<int:dataset_id>/select-typology/', frontend_views.typology_select_view, name='typology_select'),
    path('health/', frontend_views.health_check_view, name='health_check'),
    path('', frontend_views.dashboard_view, name='dashboard'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
