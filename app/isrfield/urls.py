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
from frontend import views as frontend_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('register/', frontend_views.register_view, name='register'),
    path('profile/', frontend_views.profile_view, name='profile'),
    path('users/', frontend_views.user_management_view, name='user_management'),
    path('users/edit/<int:user_id>/', frontend_views.edit_user_view, name='edit_user'),
    path('users/delete/<int:user_id>/', frontend_views.delete_user_view, name='delete_user'),
    path('groups/create/', frontend_views.create_group_view, name='create_group'),
    path('users/groups/<int:user_id>/', frontend_views.modify_user_groups_view, name='modify_user_groups'),
    path('datasets/', frontend_views.dataset_list_view, name='dataset_list'),
    path('datasets/create/', frontend_views.dataset_create_view, name='dataset_create'),
    path('datasets/<int:dataset_id>/', frontend_views.dataset_detail_view, name='dataset_detail'),
    path('datasets/<int:dataset_id>/edit/', frontend_views.dataset_edit_view, name='dataset_edit'),
    path('datasets/<int:dataset_id>/access/', frontend_views.dataset_access_view, name='dataset_access'),
    path('', frontend_views.topbar_view, name='topbar'),
]
