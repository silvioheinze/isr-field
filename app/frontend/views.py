from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from django.shortcuts import redirect

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.models import User, Group
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.contrib.auth.forms import UserChangeForm, PasswordChangeForm
from django.contrib.auth.models import Group
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.models import Group
from django import forms
from .models import AuditLog, DataSet, DataGeometry, DataEntry
from django.contrib.auth.decorators import login_required, permission_required
import json
from django.contrib.auth import update_session_auth_hash
from django.contrib.gis.geos import Point

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
    """User profile view with email and password change functionality"""
    user = request.user
    message = None
    message_type = None
    
    if request.method == 'POST':
        if 'change_email' in request.POST:
            # Handle email change
            new_email = request.POST.get('email')
            if new_email and new_email != user.email:
                user.email = new_email
                user.save()
                message = 'Email updated successfully.'
                message_type = 'success'
            else:
                message = 'Please provide a valid email address.'
                message_type = 'error'
                
        elif 'change_password' in request.POST:
            # Handle password change
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, password_form.user)
                message = 'Password changed successfully.'
                message_type = 'success'
            else:
                message = 'Please correct the password errors below.'
                message_type = 'error'
    
    # Create password form for display
    password_form = PasswordChangeForm(user)
    
    return render(request, 'frontend/profile.html', {
        'user': user,
        'password_form': password_form,
        'message': message,
        'message_type': message_type
    })


def is_manager(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name='manager').exists())

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

@login_required
def dataset_data_input_view(request, dataset_id):
    """Data input view with map and entry editing"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if not dataset.can_access(request.user):
        return HttpResponseForbidden('You do not have permission to view this dataset.')
    
    # Get all geometries for this dataset with their entries
    geometries = DataGeometry.objects.filter(dataset=dataset).prefetch_related('entries')
    
    # Prepare map data
    map_data = []
    for geometry in geometries:
        map_point = {
            'id': geometry.id,
            'id_kurz': geometry.id_kurz,
            'address': geometry.address,
            'lat': geometry.geometry.y,
            'lng': geometry.geometry.x,
            'entries_count': geometry.entries.count(),
            'entries': []
        }
        
        # Add entry data for this geometry
        for entry in geometry.entries.all():
            map_point['entries'].append({
                'id': entry.id,
                'name': entry.name,
                'usage_code1': entry.usage_code1,
                'usage_code2': entry.usage_code2,
                'usage_code3': entry.usage_code3,
                'cat_inno': entry.cat_inno,
                'cat_wert': entry.cat_wert,
                'cat_fili': entry.cat_fili,
                'year': entry.year
            })
        
        map_data.append(map_point)
    
    return render(request, 'frontend/dataset_data_input.html', {
        'dataset': dataset,
        'geometries': geometries,
        'map_data': json.dumps(map_data)
    })

@login_required
def entry_edit_view(request, entry_id):
    """Edit a specific DataEntry"""
    entry = get_object_or_404(DataEntry, pk=entry_id)
    geometry = entry.geometry
    dataset = geometry.dataset
    
    if not dataset.can_access(request.user):
        return HttpResponseForbidden('You do not have permission to edit this entry.')
    
    if request.method == 'POST':
        entry.name = request.POST.get('name')
        entry.usage_code1 = int(request.POST.get('usage_code1', 0))
        entry.usage_code2 = int(request.POST.get('usage_code2', 0))
        entry.usage_code3 = int(request.POST.get('usage_code3', 0))
        entry.cat_inno = int(request.POST.get('cat_inno', 0))
        entry.cat_wert = int(request.POST.get('cat_wert', 0))
        entry.cat_fili = int(request.POST.get('cat_fili', 0))
        entry.year = int(request.POST.get('year', 2024))
        entry.save()
        
        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='edited_entry',
            target=f'entry:{entry.id}'
        )
        
        messages.success(request, 'Entry updated successfully.')
        return redirect('dataset_data_input', dataset_id=dataset.id)
    
    return render(request, 'frontend/entry_edit.html', {'entry': entry})

@login_required
def entry_create_view(request, geometry_id):
    """Create a new DataEntry for a specific geometry"""
    geometry = get_object_or_404(DataGeometry, pk=geometry_id)
    dataset = geometry.dataset
    
    if not dataset.can_access(request.user):
        return HttpResponseForbidden('You do not have permission to create entries for this dataset.')
    
    if request.method == 'POST':
        entry = DataEntry.objects.create(
            geometry=geometry,
            name=request.POST.get('name'),
            usage_code1=int(request.POST.get('usage_code1', 0)),
            usage_code2=int(request.POST.get('usage_code2', 0)),
            usage_code3=int(request.POST.get('usage_code3', 0)),
            cat_inno=int(request.POST.get('cat_inno', 0)),
            cat_wert=int(request.POST.get('cat_wert', 0)),
            cat_fili=int(request.POST.get('cat_fili', 0)),
            year=int(request.POST.get('year', 2024)),
            user=request.user
        )
        
        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='created_entry',
            target=f'entry:{entry.id}'
        )
        
        messages.success(request, 'Entry created successfully.')
        return redirect('dataset_data_input', dataset_id=dataset.id)
    
    return render(request, 'frontend/entry_create.html', {'geometry': geometry}) 

@login_required
def geometry_create_view(request, dataset_id):
    """Create a new geometry point for a dataset"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if not dataset.can_access(request.user):
        return HttpResponseForbidden('You do not have permission to create geometries for this dataset.')
    
    if request.method == 'POST':
        try:
            address = request.POST.get('address')
            id_kurz = request.POST.get('id_kurz')
            lat = float(request.POST.get('lat'))
            lng = float(request.POST.get('lng'))
            
            # Validate required fields
            if not address or not id_kurz:
                messages.error(request, 'Address and ID are required.')
                return redirect('dataset_data_input', dataset_id=dataset.id)
            
            # Check if id_kurz already exists
            if DataGeometry.objects.filter(id_kurz=id_kurz).exists():
                messages.error(request, f'Geometry with ID "{id_kurz}" already exists.')
                return redirect('dataset_data_input', dataset_id=dataset.id)
            
            # Validate coordinates
            if lat < -90 or lat > 90 or lng < -180 or lng > 180:
                messages.error(request, 'Invalid coordinates provided.')
                return redirect('dataset_data_input', dataset_id=dataset.id)
            
            # Create the geometry point
            geometry = DataGeometry.objects.create(
                dataset=dataset,
                address=address,
                id_kurz=id_kurz,
                geometry=Point(lng, lat, srid=4326),
                user=request.user
            )
            
            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action='created_geometry',
                target=f'geometry:{geometry.id}'
            )
            
            messages.success(request, f'Geometry "{id_kurz}" created successfully.')
            return redirect('dataset_data_input', dataset_id=dataset.id)
            
        except (ValueError, TypeError) as e:
            messages.error(request, 'Invalid data provided. Please check your coordinates.')
            return redirect('dataset_data_input', dataset_id=dataset.id)
        except Exception as e:
            messages.error(request, f'Error creating geometry: {str(e)}')
            return redirect('dataset_data_input', dataset_id=dataset.id)
    
    return render(request, 'frontend/geometry_create.html', {'dataset': dataset}) 