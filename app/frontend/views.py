from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from django.shortcuts import redirect

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.models import User, Group
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import Group
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.models import Group
from django import forms
from .models import AuditLog, DataSet
from django.contrib.auth.decorators import login_required, permission_required

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']

@login_required
def topbar_view(request):
    """Dashboard view with user's accessible datasets"""
    accessible_datasets = []
    for dataset in DataSet.objects.all():
        if dataset.can_access(request.user):
            accessible_datasets.append(dataset)
    
    return render(request, 'frontend/topbar.html', {
        'datasets': accessible_datasets[:5]  # Show first 5 datasets
    })


def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'frontend/register.html', {'form': form})


@login_required
def profile_view(request):
    return render(request, 'frontend/profile.html', {'user': request.user})


def is_manager(user):
    return user.is_authenticated and user.groups.filter(name='manager').exists()

@login_required
def user_management_view(request):
    if not is_manager(request.user):
        return HttpResponseForbidden('You do not have permission to view this page.')
    users = User.objects.all()
    return render(request, 'frontend/user_management.html', {'users': users})

@login_required
def edit_user_view(request, user_id):
    if not is_manager(request.user):
        return HttpResponseForbidden('You do not have permission to edit users.')
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            # Update groups
            group_ids = request.POST.getlist('groups')
            user.groups.set(Group.objects.filter(id__in=group_ids))
            messages.success(request, 'User updated successfully.')
            return redirect('user_management')
    else:
        form = UserChangeForm(instance=user)
    all_groups = Group.objects.all()
    user_groups = user.groups.values_list('id', flat=True)
    return render(request, 'frontend/edit_user.html', {'form': form, 'user_obj': user, 'all_groups': all_groups, 'user_groups': user_groups})

@login_required
def delete_user_view(request, user_id):
    if not is_manager(request.user):
        return HttpResponseForbidden('You do not have permission to delete users.')
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('user_management')
    return render(request, 'frontend/delete_user.html', {'user_obj': user})

@login_required
def create_group_view(request):
    if not is_manager(request.user):
        return HttpResponseForbidden('You do not have permission to create groups.')
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Group created successfully.')
            return redirect('user_management')
    else:
        form = GroupForm()
    return render(request, 'frontend/create_group.html', {'form': form})

@login_required
def modify_user_groups_view(request, user_id):
    if not is_manager(request.user):
        return HttpResponseForbidden('You do not have permission to modify user groups.')
    user = get_object_or_404(User, pk=user_id)
    all_groups = Group.objects.all()
    if request.method == 'POST':
        group_ids = request.POST.getlist('groups')
        user.groups.set(Group.objects.filter(id__in=group_ids))
        messages.success(request, 'User groups updated successfully.')
        return redirect('user_management')
    user_groups = user.groups.values_list('id', flat=True)
    return render(request, 'frontend/modify_user_groups.html', {'user_obj': user, 'all_groups': all_groups, 'user_groups': user_groups})

@login_required
def dataset_list_view(request):
    """List datasets that the user can access"""
    accessible_datasets = []
    for dataset in DataSet.objects.all():
        if dataset.can_access(request.user):
            accessible_datasets.append(dataset)
    return render(request, 'frontend/dataset_list.html', {'datasets': accessible_datasets})

@login_required
def dataset_create_view(request):
    """Create a new dataset"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        is_public = request.POST.get('is_public') == 'on'

        dataset = DataSet.objects.create(
            name=name,
            description=description,
            owner=request.user,
            is_public=is_public
        )

        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='created_dataset',
            target=f'dataset:{dataset.id}'
        )

        messages.success(request, 'Dataset created successfully.')
        return redirect('dataset_list')

    return render(request, 'frontend/dataset_create.html')

@login_required
def dataset_detail_view(request, dataset_id):
    """View dataset details"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if not dataset.can_access(request.user):
        return HttpResponseForbidden('You do not have permission to view this dataset.')

    return render(request, 'frontend/dataset_detail.html', {'dataset': dataset})

@login_required
def dataset_edit_view(request, dataset_id):
    """Edit dataset (only owner can edit)"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if dataset.owner != request.user:
        return HttpResponseForbidden('You do not have permission to edit this dataset.')

    if request.method == 'POST':
        dataset.name = request.POST.get('name')
        dataset.description = request.POST.get('description', '')
        dataset.is_public = request.POST.get('is_public') == 'on'
        dataset.save()

        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='edited_dataset',
            target=f'dataset:{dataset.id}'
        )

        messages.success(request, 'Dataset updated successfully.')
        return redirect('dataset_detail', dataset_id=dataset.id)

    return render(request, 'frontend/dataset_edit.html', {'dataset': dataset})

@login_required
def dataset_access_view(request, dataset_id):
    """Manage dataset access (only owner can manage access)"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if dataset.owner != request.user:
        return HttpResponseForbidden('You do not have permission to manage access to this dataset.')

    if request.method == 'POST':
        user_ids = request.POST.getlist('shared_users')
        dataset.shared_with.set(User.objects.filter(id__in=user_ids))

        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='modified_dataset_access',
            target=f'dataset:{dataset.id}'
        )

        messages.success(request, 'Dataset access updated successfully.')
        return redirect('dataset_detail', dataset_id=dataset.id)

    all_users = User.objects.exclude(id=request.user.id)
    shared_users = dataset.shared_with.values_list('id', flat=True)

    return render(request, 'frontend/dataset_access.html', {
        'dataset': dataset,
        'all_users': all_users,
        'shared_users': shared_users
    }) 