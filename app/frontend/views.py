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
from .models import AuditLog, DataSet, DataGeometry, DataEntry, DataEntryFile
from django.contrib.auth.decorators import login_required, permission_required
import json
import csv
import io
from django.contrib.auth import update_session_auth_hash
from django.contrib.gis.geos import Point
from django.http import HttpResponse, Http404, JsonResponse
from django.conf import settings
from django.db import transaction
from django.core.exceptions import ValidationError
import os
import mimetypes

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
    
    # Get counts for geometries and data entries
    geometries_count = DataGeometry.objects.filter(dataset=dataset).count()
    data_entries_count = DataEntry.objects.filter(geometry__dataset=dataset).count()
    
    return render(request, 'frontend/dataset_detail.html', {
        'dataset': dataset,
        'geometries_count': geometries_count,
        'data_entries_count': data_entries_count
    })

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
            'user': geometry.user.username if geometry.user else 'Unknown',
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
                'year': entry.year,
                'user': entry.user.username if entry.user else 'Unknown'
            })
        
        map_data.append(map_point)
    
    return render(request, 'frontend/dataset_data_input.html', {
        'dataset': dataset,
        'geometries': geometries
    })


@login_required
def dataset_map_data_view(request, dataset_id):
    """API endpoint to get map data for a dataset"""
    try:
        dataset = get_object_or_404(DataSet, pk=dataset_id)
        if not dataset.can_access(request.user):
            return HttpResponseForbidden('You do not have permission to view this dataset.')
        
        # Get map bounds from request parameters
        bounds = request.GET.get('bounds')
        
        if bounds:
            try:
                # Parse bounds: "south,west,north,east"
                south, west, north, east = map(float, bounds.split(','))
                
                # Filter geometries within the bounds using spatial lookups
                from django.contrib.gis.geos import Polygon
                from django.contrib.gis.db.models.functions import Transform
                
                # Create a bounding box polygon
                bbox = Polygon.from_bbox((west, south, east, north))
                
                # Filter geometries within the bounds
                geometries = DataGeometry.objects.filter(
                    dataset=dataset,
                    geometry__within=bbox
                ).prefetch_related('entries')
            except (ValueError, TypeError) as e:
                # If bounds parsing fails, get all geometries
                geometries = DataGeometry.objects.filter(dataset=dataset).prefetch_related('entries')
        else:
            # No bounds provided, get all geometries
            geometries = DataGeometry.objects.filter(dataset=dataset).prefetch_related('entries')
        
        # Prepare map data
        map_data = []
        for geometry in geometries:
            try:
                map_point = {
                    'id': geometry.id,
                    'id_kurz': geometry.id_kurz,
                    'address': geometry.address,
                    'lat': geometry.geometry.y,
                    'lng': geometry.geometry.x,
                    'entries_count': geometry.entries.count(),
                    'user': geometry.user.username if geometry.user else 'Unknown',
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
                        'year': entry.year,
                        'user': entry.user.username if entry.user else 'Unknown'
                    })
                
                map_data.append(map_point)
            except Exception as e:
                continue
        
        return JsonResponse({'map_data': map_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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

@login_required
def file_upload_view(request, entry_id):
    """Upload files for a DataEntry"""
    entry = get_object_or_404(DataEntry, pk=entry_id)
    geometry = entry.geometry
    dataset = geometry.dataset
    
    if not dataset.can_access(request.user):
        return HttpResponseForbidden('You do not have permission to upload files for this entry.')
    
    if request.method == 'POST':
        uploaded_files = request.FILES.getlist('files')
        description = request.POST.get('description', '')
        
        for uploaded_file in uploaded_files:
            # Get file information
            file_type, _ = mimetypes.guess_type(uploaded_file.name)
            file_size = uploaded_file.size
            
            # Create DataEntryFile
            entry_file = DataEntryFile.objects.create(
                entry=entry,
                file=uploaded_file,
                filename=uploaded_file.name,
                file_type=file_type or 'application/octet-stream',
                file_size=file_size,
                upload_user=request.user,
                description=description
            )
            
            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action='uploaded_file',
                target=f'file:{entry_file.id}'
            )
        
        messages.success(request, f'{len(uploaded_files)} file(s) uploaded successfully.')
        return redirect('entry_detail', entry_id=entry.id)
    
    return render(request, 'frontend/file_upload.html', {'entry': entry})

@login_required
def file_download_view(request, file_id):
    """Download a file"""
    entry_file = get_object_or_404(DataEntryFile, pk=file_id)
    entry = entry_file.entry
    geometry = entry.geometry
    dataset = geometry.dataset
    
    if not dataset.can_access(request.user):
        return HttpResponseForbidden('You do not have permission to download this file.')
    
    # Check if file exists
    if not os.path.exists(entry_file.file.path):
        raise Http404("File not found")
    
    # Open and serve the file
    with open(entry_file.file.path, 'rb') as f:
        response = HttpResponse(f.read(), content_type=entry_file.file_type)
        response['Content-Disposition'] = f'attachment; filename="{entry_file.filename}"'
        return response

@login_required
def file_delete_view(request, file_id):
    """Delete a file"""
    entry_file = get_object_or_404(DataEntryFile, pk=file_id)
    entry = entry_file.entry
    geometry = entry.geometry
    dataset = geometry.dataset
    
    if not dataset.can_access(request.user):
        return HttpResponseForbidden('You do not have permission to delete this file.')
    
    if request.method == 'POST':
        # Log the action before deletion
        AuditLog.objects.create(
            user=request.user,
            action='deleted_file',
            target=f'file:{entry_file.id}'
        )
        
        # Delete the file
        entry_file.delete()
        messages.success(request, 'File deleted successfully.')
        return redirect('entry_detail', entry_id=entry.id)
    
    return render(request, 'frontend/file_delete.html', {'entry_file': entry_file})

@login_required
def entry_detail_view(request, entry_id):
    """Detailed view of a DataEntry with its files"""
    entry = get_object_or_404(DataEntry, pk=entry_id)
    geometry = entry.geometry
    dataset = geometry.dataset
    
    if not dataset.can_access(request.user):
        return HttpResponseForbidden('You do not have permission to view this entry.')
    
    return render(request, 'frontend/entry_detail.html', {'entry': entry})


@login_required
def dataset_csv_import_view(request, dataset_id):
    """Import CSV data into a dataset"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if not dataset.can_access(request.user):
        return HttpResponseForbidden('You do not have permission to import data into this dataset.')
    
    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, 'Please select a CSV file to import.')
            return render(request, 'frontend/dataset_csv_import.html', {'dataset': dataset})
        
        csv_file = request.FILES['csv_file']
        
        # Check file extension
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a valid CSV file.')
            return render(request, 'frontend/dataset_csv_import.html', {'dataset': dataset})
        
        try:
            # Read CSV file
            decoded_file = csv_file.read().decode('utf-8')
            csv_data = csv.DictReader(io.StringIO(decoded_file))
            
            imported_count = 0
            errors = []
            
            with transaction.atomic():
                for row_num, row in enumerate(csv_data, start=2):  # Start at 2 because row 1 is header
                    try:
                        # Extract data from CSV row
                        id_kurz = row.get('ID', '').strip()
                        address = row.get('ADRESSE', '').strip()
                        
                        # Extract coordinates - handle different possible column names
                        x_coord = None
                        y_coord = None
                        
                        # Try different possible coordinate column names
                        if 'GEB_X' in row and 'GEB_Y' in row:
                            x_coord = row['GEB_X']
                            y_coord = row['GEB_Y']
                        elif 'X' in row and 'Y' in row:
                            x_coord = row['X']
                            y_coord = row['Y']
                        elif 'LONGITUDE' in row and 'LATITUDE' in row:
                            x_coord = row['LONGITUDE']
                            y_coord = row['LATITUDE']
                        elif 'LON' in row and 'LAT' in row:
                            x_coord = row['LON']
                            y_coord = row['LAT']
                        
                        # Validate required fields
                        if not id_kurz:
                            errors.append(f"Row {row_num}: Missing ID")
                            continue
                        
                        if not address:
                            errors.append(f"Row {row_num}: Missing address")
                            continue
                        
                        if x_coord is None or y_coord is None:
                            errors.append(f"Row {row_num}: Missing coordinates")
                            continue
                        
                        # Check if geometry already exists
                        if DataGeometry.objects.filter(id_kurz=id_kurz).exists():
                            errors.append(f"Row {row_num}: Geometry with ID '{id_kurz}' already exists")
                            continue
                        
                        # Convert coordinates to float
                        try:
                            x_coord = float(x_coord)
                            y_coord = float(y_coord)
                        except ValueError:
                            errors.append(f"Row {row_num}: Invalid coordinates")
                            continue
                        
                        # Create geometry point
                        geometry = DataGeometry.objects.create(
                            dataset=dataset,
                            address=address,
                            id_kurz=id_kurz,
                            geometry=Point(x_coord, y_coord, srid=4326),
                            user=request.user
                        )
                        
                        # Create data entry if usage data is available
                        usage_code1 = row.get('2016_NUTZUNG') or row.get('2022_NUTZUNG') or row.get('NUTZUNG')
                        usage_code2 = row.get('2016_CAT_INNO') or row.get('2022_CAT_INNO') or row.get('CAT_INNO')
                        usage_code3 = row.get('2016_CAT_WERT') or row.get('2022_CAT_WERT') or row.get('CAT_WERT')
                        cat_inno = row.get('2016_CAT_INNO') or row.get('2022_CAT_INNO') or row.get('CAT_INNO')
                        cat_wert = row.get('2016_CAT_WERT') or row.get('2022_CAT_WERT') or row.get('CAT_WERT')
                        cat_fili = row.get('2016_CAT_FILI') or row.get('2022_CAT_FILI') or row.get('CAT_FILI')
                        year = row.get('YEAR') or '2022'  # Default to 2022 if not specified
                        
                        # Convert to integers if they exist and are not empty
                        try:
                            if usage_code1 and usage_code1.strip():
                                usage_code1 = int(usage_code1)
                            else:
                                usage_code1 = 0
                                
                            if usage_code2 and usage_code2.strip():
                                usage_code2 = int(usage_code2)
                            else:
                                usage_code2 = 0
                                
                            if usage_code3 and usage_code3.strip():
                                usage_code3 = int(usage_code3)
                            else:
                                usage_code3 = 0
                                
                            if cat_inno and cat_inno.strip():
                                cat_inno = int(cat_inno)
                            else:
                                cat_inno = 0
                                
                            if cat_wert and cat_wert.strip():
                                cat_wert = int(cat_wert)
                            else:
                                cat_wert = 0
                                
                            if cat_fili and cat_fili.strip():
                                cat_fili = int(cat_fili)
                            else:
                                cat_fili = 0
                                
                            if year and year.strip():
                                year = int(year)
                            else:
                                year = 2022
                                
                        except ValueError:
                            # If conversion fails, use default values
                            usage_code1 = usage_code2 = usage_code3 = cat_inno = cat_wert = cat_fili = 0
                            year = 2022
                        
                        # Create data entry
                        DataEntry.objects.create(
                            geometry=geometry,
                            name=f"Entry for {id_kurz}",
                            usage_code1=usage_code1,
                            usage_code2=usage_code2,
                            usage_code3=usage_code3,
                            cat_inno=cat_inno,
                            cat_wert=cat_wert,
                            cat_fili=cat_fili,
                            year=year,
                            user=request.user
                        )
                        
                        imported_count += 1
                        
                    except Exception as e:
                        errors.append(f"Row {row_num}: {str(e)}")
                        continue
            
            # Log the import action
            AuditLog.objects.create(
                user=request.user,
                action='csv_import',
                target=f'dataset:{dataset.id}',
                details=f'Imported {imported_count} records'
            )
            
            if imported_count > 0:
                messages.success(request, f'Successfully imported {imported_count} records.')
            
            if errors:
                error_message = f'Import completed with {len(errors)} errors: ' + '; '.join(errors[:10])
                if len(errors) > 10:
                    error_message += f' (and {len(errors) - 10} more errors)'
                messages.warning(request, error_message)
            
            return redirect('dataset_detail', dataset_id=dataset.id)
            
        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')
            return render(request, 'frontend/dataset_csv_import.html', {'dataset': dataset})
    
    return render(request, 'frontend/dataset_csv_import.html', {'dataset': dataset}) 