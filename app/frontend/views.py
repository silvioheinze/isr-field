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
from .models import AuditLog, DataSet, DataGeometry, DataEntry, DataEntryFile, Typology, TypologyEntry
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
import logging
from datetime import datetime
from django.db import connection, IntegrityError

# Set up logging for import debugging
logger = logging.getLogger(__name__)

def health_check_view(request):
    """Health check endpoint for Docker container"""
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=500)

def get_coordinate_system_name(srid):
    """Get human-readable name for coordinate system SRID"""
    coordinate_systems = {
        4326: "WGS84 (Latitude/Longitude)",
        31256: "MGI Austria GK M34",
        31257: "MGI Austria GK M31", 
        31258: "MGI Austria GK M28",
        3857: "Web Mercator",
    }
    return coordinate_systems.get(srid, f"EPSG:{srid}")

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name']

@login_required
def dashboard_view(request):
    """Dashboard view with user's accessible datasets"""
    accessible_datasets = []
    for dataset in DataSet.objects.all():
        if dataset.can_access(request.user):
            accessible_datasets.append(dataset)
    
    return render(request, 'frontend/dashboard.html', {
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
    groups = Group.objects.all()
    return render(request, 'frontend/user_management.html', {'users': users, 'groups': groups})

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
def create_user_view(request):
    if not is_manager(request.user):
        return HttpResponseForbidden('You do not have permission to create users.')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Set groups
            group_ids = request.POST.getlist('groups')
            user.groups.set(Group.objects.filter(id__in=group_ids))
            messages.success(request, 'User created successfully.')
            return redirect('user_management')
    else:
        form = UserCreationForm()
    all_groups = Group.objects.all()
    return render(request, 'frontend/create_user.html', {'form': form, 'all_groups': all_groups})

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
        group_ids = request.POST.getlist('shared_groups')
        
        # Update user access
        dataset.shared_with.set(User.objects.filter(id__in=user_ids))
        
        # Update group access
        dataset.shared_with_groups.set(Group.objects.filter(id__in=group_ids))
        
        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='modified_dataset_access',
            target=f'dataset:{dataset.id}'
        )
        
        messages.success(request, 'Dataset access updated successfully.')
        return redirect('dataset_detail', dataset_id=dataset.id)
    
    all_users = User.objects.exclude(id=request.user.id)
    all_groups = Group.objects.all()
    shared_users = dataset.shared_with.values_list('id', flat=True)
    shared_groups = dataset.shared_with_groups.values_list('id', flat=True)
    
    return render(request, 'frontend/dataset_access.html', {
        'dataset': dataset,
        'all_users': all_users,
        'all_groups': all_groups,
        'shared_users': shared_users,
        'shared_groups': shared_groups
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
    
    # Get typology data if linked
    typology_data = None
    if dataset.typology:
        typology_entries = dataset.typology.entries.all().order_by('code')
        typology_data = {
            'id': dataset.typology.id,
            'name': dataset.typology.name,
            'entries': [
                {
                    'code': entry.code,
                    'category': entry.category,
                    'name': entry.name
                }
                for entry in typology_entries
            ]
        }
    
    return render(request, 'frontend/dataset_data_input.html', {
        'dataset': dataset,
        'geometries': geometries,
        'typology_data': typology_data
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
def dataset_clear_data_view(request, dataset_id):
    """Clear all geometry points and data entries from a dataset"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    
    # Only dataset owner can clear data
    if dataset.owner != request.user:
        return HttpResponseForbidden('You do not have permission to clear data from this dataset.')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get counts before deletion for logging
                geometry_count = DataGeometry.objects.filter(dataset=dataset).count()
                entry_count = DataEntry.objects.filter(geometry__dataset=dataset).count()
                file_count = DataEntryFile.objects.filter(entry__geometry__dataset=dataset).count()
                
                # Delete all files first (to avoid foreign key constraints)
                DataEntryFile.objects.filter(entry__geometry__dataset=dataset).delete()
                
                # Delete all data entries
                DataEntry.objects.filter(geometry__dataset=dataset).delete()
                
                # Delete all geometry points
                DataGeometry.objects.filter(dataset=dataset).delete()
                
                # Log the action
                AuditLog.objects.create(
                    user=request.user,
                    action='cleared_dataset_data',
                    target=f'dataset:{dataset.id} - Deleted {geometry_count} geometries, {entry_count} entries, and {file_count} files'
                )
                
                messages.success(request, f'Successfully cleared all data from "{dataset.name}". Deleted {geometry_count} geometry points, {entry_count} data entries, and {file_count} files.')
                
        except Exception as e:
            messages.error(request, f'Error clearing dataset data: {str(e)}')
            return redirect('dataset_detail', dataset_id=dataset.id)
        
        return redirect('dataset_detail', dataset_id=dataset.id)
    
    # GET request - show confirmation page
    geometry_count = DataGeometry.objects.filter(dataset=dataset).count()
    entry_count = DataEntry.objects.filter(geometry__dataset=dataset).count()
    file_count = DataEntryFile.objects.filter(entry__geometry__dataset=dataset).count()
    
    return render(request, 'frontend/dataset_clear_data.html', {
        'dataset': dataset,
        'geometry_count': geometry_count,
        'entry_count': entry_count,
        'file_count': file_count
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
        try:
            # Debug logging
            print(f"POST data: {request.POST}")
            print(f"FILES: {request.FILES}")
            
            # Ensure media directory exists
            from django.conf import settings
            import os
            media_root = settings.MEDIA_ROOT
            if not os.path.exists(media_root):
                os.makedirs(media_root)
                print(f"Created media directory: {media_root}")
            
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
            
            # Handle file uploads
            uploaded_files = request.FILES.getlist('files')
            for uploaded_file in uploaded_files:
                # Get file information
                file_type, _ = mimetypes.guess_type(uploaded_file.name)
                file_size = uploaded_file.size
                
                # Create the file entry
                entry_file = DataEntryFile.objects.create(
                    entry=entry,
                    file=uploaded_file,
                    filename=uploaded_file.name,
                    file_type=file_type or 'application/octet-stream',
                    file_size=file_size,
                    description='Photo uploaded with entry creation',
                    upload_user=request.user
                )
                
                # Debug: Print file information after creation
                print(f"Created file: {entry_file.filename}")
                print(f"File URL: {entry_file.file.url}")
                print(f"File path: {entry_file.file.path}")
                print(f"File exists: {os.path.exists(entry_file.file.path)}")
            
            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action='created_entry',
                target=f'entry:{entry.id}'
            )
            
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'entry_id': entry.id})
            else:
                messages.success(request, 'Entry created successfully.')
                return redirect('dataset_data_input', dataset_id=dataset.id)
        except Exception as e:
            # Debug logging
            print(f"Error creating entry: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
            else:
                messages.error(request, f'Error creating entry: {str(e)}')
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
    
    # Debug: Print file information
    print(f"Entry {entry_id} has {entry.files.count()} files")
    for file in entry.files.all():
        print(f"File: {file.filename}, URL: {file.file.url}, Path: {file.file.path}")
        print(f"File exists: {os.path.exists(file.file.path)}")
    
    return render(request, 'frontend/entry_detail.html', {'entry': entry})


@login_required
def dataset_csv_import_view(request, dataset_id):
    """Import CSV data into a dataset"""
    logger.info(f"Starting CSV import for dataset {dataset_id} by user {request.user.username}")
    
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if not dataset.can_access(request.user):
        logger.warning(f"User {request.user.username} attempted to access dataset {dataset_id} without permission")
        return HttpResponseForbidden('You do not have permission to import data into this dataset.')
    
    if request.method == 'POST':
        logger.info("Processing POST request for CSV import")
        
        if 'csv_file' not in request.FILES:
            logger.error("No CSV file found in request.FILES")
            logger.debug(f"Available files in request.FILES: {list(request.FILES.keys())}")
            messages.error(request, 'Please select a CSV file to import.')
            return render(request, 'frontend/dataset_csv_import.html', {'dataset': dataset})
        
        csv_file = request.FILES['csv_file']
        logger.info(f"CSV file received: {csv_file.name}, size: {csv_file.size} bytes")
        
        # Check file extension
        if not csv_file.name.endswith('.csv'):
            logger.error(f"Invalid file type: {csv_file.name}")
            messages.error(request, 'Please upload a valid CSV file.')
            return render(request, 'frontend/dataset_csv_import.html', {'dataset': dataset})
        
        try:
            # Read CSV file
            logger.info("Reading CSV file content")
            decoded_file = csv_file.read().decode('utf-8')
            logger.debug(f"CSV content length: {len(decoded_file)} characters")
            logger.debug(f"First 500 characters of CSV: {decoded_file[:500]}")
            
            csv_data = csv.DictReader(io.StringIO(decoded_file))
            logger.info(f"CSV headers detected: {csv_data.fieldnames}")
            
            imported_count = 0
            errors = []
            
            with transaction.atomic():
                logger.info("Starting transaction for CSV import")
                row_count = 0
                for row_num, row in enumerate(csv_data, start=2):  # Start at 2 because row 1 is header
                    row_count += 1
                    logger.debug(f"Processing row {row_num}: {row}")
                    try:
                        # Extract data from CSV row
                        id_kurz = row.get('ID', '').strip()
                        address = row.get('ADRESSE', '').strip()
                        
                        # Extract coordinates - handle different possible column names
                        x_coord = None
                        y_coord = None
                        
                        logger.debug(f"Available columns in row: {list(row.keys())}")
                        
                        # Try different possible coordinate column names
                        if 'GEB_X' in row and 'GEB_Y' in row:
                            x_coord = row['GEB_X']
                            y_coord = row['GEB_Y']
                            logger.debug(f"Using GEB_X/GEB_Y coordinates: {x_coord}, {y_coord}")
                        elif 'X' in row and 'Y' in row:
                            x_coord = row['X']
                            y_coord = row['Y']
                            logger.debug(f"Using X/Y coordinates: {x_coord}, {y_coord}")
                        elif 'LONGITUDE' in row and 'LATITUDE' in row:
                            x_coord = row['LONGITUDE']
                            y_coord = row['LATITUDE']
                            logger.debug(f"Using LONGITUDE/LATITUDE coordinates: {x_coord}, {y_coord}")
                        elif 'LON' in row and 'LAT' in row:
                            x_coord = row['LON']
                            y_coord = row['LAT']
                            logger.debug(f"Using LON/LAT coordinates: {x_coord}, {y_coord}")
                        else:
                            logger.warning(f"No coordinate columns found in row {row_num}. Available columns: {list(row.keys())}")
                        
                        # Validate required fields
                        logger.debug(f"Validating row {row_num}: ID='{id_kurz}', Address='{address}', X='{x_coord}', Y='{y_coord}'")
                        
                        if not id_kurz:
                            logger.warning(f"Row {row_num}: Missing ID")
                            errors.append(f"Row {row_num}: Missing ID")
                            continue
                        
                        if not address:
                            logger.warning(f"Row {row_num}: Missing address, using default")
                            address = f"Unknown Address ({id_kurz})"
                        
                        if x_coord is None or y_coord is None:
                            logger.warning(f"Row {row_num}: Missing coordinates")
                            errors.append(f"Row {row_num}: Missing coordinates")
                            continue
                        
                        # Check if geometry already exists
                        existing_geometry = DataGeometry.objects.filter(id_kurz=id_kurz).exists()
                        logger.debug(f"Row {row_num}: Geometry with ID '{id_kurz}' already exists: {existing_geometry}")
                        if existing_geometry:
                            logger.warning(f"Row {row_num}: Geometry with ID '{id_kurz}' already exists")
                            errors.append(f"Row {row_num}: Geometry with ID '{id_kurz}' already exists")
                            continue
                        
                        # Convert coordinates to float
                        try:
                            logger.debug(f"Converting coordinates to float: x='{x_coord}', y='{y_coord}'")
                            x_coord = float(x_coord)
                            y_coord = float(y_coord)
                            logger.debug(f"Converted coordinates: x={x_coord}, y={y_coord}")
                        except ValueError as e:
                            logger.error(f"Row {row_num}: Failed to convert coordinates to float: {e}")
                            errors.append(f"Row {row_num}: Invalid coordinates")
                            continue
                        
                        # Detect coordinate projection and transform if needed
                        from django.contrib.gis.geos import Point
                        from django.contrib.gis.gdal import SpatialReference, CoordTransform
                        
                        # Check if coordinates are likely in a different projection
                        # Common Austrian coordinate systems:
                        # - EPSG:4326 (WGS84) - lat/lng: lat ~47-49, lng ~9-18
                        # - EPSG:31256 (MGI Austria GK M34) - x ~500000-900000, y ~4000000-5000000
                        # - EPSG:31257 (MGI Austria GK M31) - x ~300000-700000, y ~4000000-5000000
                        # - EPSG:31258 (MGI Austria GK M28) - x ~100000-500000, y ~4000000-5000000
                        # - EPSG:31256 (MGI Austria GK M34) - x ~100-2000, y ~330000-350000 (scaled coordinates)
                        
                        # Get coordinate system from form or use auto-detection
                        coordinate_system = request.POST.get('coordinate_system', 'auto')
                        logger.debug(f"Coordinate system selection: {coordinate_system}")
                        
                        if coordinate_system == 'auto':
                            # Auto-detect projection based on coordinate ranges
                            source_srid = 4326  # Default to WGS84
                            logger.debug(f"Auto-detecting coordinate system for coordinates: x={x_coord}, y={y_coord}")
                            
                            if (x_coord >= 100000 and x_coord <= 900000 and 
                                y_coord >= 3000000 and y_coord <= 5000000):
                                # Likely Austrian projected coordinates (full scale)
                                if x_coord >= 500000 and x_coord <= 900000:
                                    source_srid = 31256  # MGI Austria GK M34
                                elif x_coord >= 300000 and x_coord <= 700000:
                                    source_srid = 31257  # MGI Austria GK M31
                                elif x_coord >= 100000 and x_coord <= 500000:
                                    source_srid = 31258  # MGI Austria GK M28
                            elif (x_coord >= 100000 and x_coord <= 900000 and 
                                  y_coord >= 3000000 and y_coord <= 4000000):
                                # Likely Austrian projected coordinates (alternative scale)
                                source_srid = 31256  # MGI Austria GK M34
                                logger.debug("Detected MGI Austria GK M34 (EPSG:31256) - alternative scale")
                            elif (x_coord >= 100 and x_coord <= 2000 and 
                                  y_coord >= 330000 and y_coord <= 350000):
                                # Likely Austrian projected coordinates (scaled down)
                                source_srid = 31256  # MGI Austria GK M34
                                logger.debug("Detected MGI Austria GK M34 (EPSG:31256) - scaled coordinates")
                            elif (x_coord >= 9 and x_coord <= 18 and 
                                  y_coord >= 47 and y_coord <= 49):
                                # Likely WGS84 lat/lng coordinates
                                source_srid = 4326
                                logger.debug("Detected WGS84 (EPSG:4326)")
                            else:
                                logger.debug(f"Using default WGS84 (EPSG:4326) for coordinates outside known ranges")
                        else:
                            # Use manually specified coordinate system
                            try:
                                source_srid = int(coordinate_system)
                                logger.debug(f"Using manually specified coordinate system: EPSG:{source_srid}")
                            except ValueError as e:
                                logger.error(f"Row {row_num}: Invalid coordinate system specified: {coordinate_system}")
                                errors.append(f"Row {row_num}: Invalid coordinate system specified")
                                continue
                        
                        # Track coordinate system for import summary
                        if 'import_summary' not in locals():
                            import_summary = {
                                'coordinate_system': source_srid,
                                'coordinate_system_name': get_coordinate_system_name(source_srid),
                                'detection_method': 'manual' if coordinate_system != 'auto' else 'auto',
                                'geometries_created': 0,
                                'entries_created': 0,
                                'rows_processed': 0,
                                'rows_skipped': 0,
                                'transformation_errors': 0
                            }
                        
                        # Create point in source projection
                        source_point = Point(x_coord, y_coord, srid=source_srid)
                        
                        # Transform to WGS84 (EPSG:4326) if needed
                        if source_srid != 4326:
                            logger.debug(f"Transforming coordinates from EPSG:{source_srid} to EPSG:4326")
                            try:
                                source_srs = SpatialReference(source_srid)
                                target_srs = SpatialReference(4326)
                                transform = CoordTransform(source_srs, target_srs)
                                source_point.transform(transform)
                                x_coord = source_point.x
                                y_coord = source_point.y
                                logger.debug(f"Transformation successful: new coordinates x={x_coord}, y={y_coord}")
                            except Exception as e:
                                logger.error(f"Row {row_num}: Coordinate transformation failed: {str(e)}")
                                errors.append(f"Row {row_num}: Coordinate transformation failed - {str(e)}")
                                import_summary['transformation_errors'] += 1
                                continue
                        else:
                            logger.debug("No transformation needed - coordinates already in WGS84")
                        
                        # Validate final WGS84 coordinates
                        logger.debug(f"Validating final WGS84 coordinates: x={x_coord}, y={y_coord}")
                        if y_coord < -90 or y_coord > 90 or x_coord < -180 or x_coord > 180:
                            logger.error(f"Row {row_num}: Invalid WGS84 coordinates after transformation: x={x_coord}, y={y_coord}")
                            errors.append(f"Row {row_num}: Invalid WGS84 coordinates after transformation")
                            continue
                        
                        # Create geometry point
                        logger.debug(f"Creating geometry point for row {row_num}: ID={id_kurz}, Address={address}, Coordinates=({x_coord}, {y_coord})")
                        try:
                            geometry = DataGeometry.objects.create(
                                dataset=dataset,
                                address=address,
                                id_kurz=id_kurz,
                                geometry=Point(x_coord, y_coord, srid=4326),
                                user=request.user
                            )
                            logger.debug(f"Successfully created geometry with ID: {geometry.id}")
                            import_summary['geometries_created'] += 1
                        except Exception as e:
                            logger.error(f"Row {row_num}: Failed to create geometry: {str(e)}")
                            errors.append(f"Row {row_num}: Failed to create geometry - {str(e)}")
                            continue
                        
                        # Create separate data entries for all year-prefixed columns
                        entries_created = 0
                        
                        # Get all column names from the CSV
                        all_columns = list(row.keys())
                        logger.debug(f"Row {row_num}: All columns: {all_columns}")
                        
                        # Find all year-prefixed columns (e.g., "2016_", "2022_", "2020_", etc.)
                        year_columns = {}
                        for column in all_columns:
                            # Check if column starts with a 4-digit year followed by underscore
                            if column and len(column) >= 5 and column[:4].isdigit() and column[4] == '_':
                                year = int(column[:4])
                                field_name = column[5:]  # Remove year prefix
                                
                                if year not in year_columns:
                                    year_columns[year] = {}
                                year_columns[year][field_name] = row.get(column)
                                logger.debug(f"Row {row_num}: Found year column {column} -> year={year}, field={field_name}, value={row.get(column)}")
                        
                        logger.debug(f"Row {row_num}: Year columns detected: {list(year_columns.keys())}")
                        
                        # Helper function to safely convert to integer, treating 'NA' and '999' as missing
                        def safe_int_convert(value, default=0):
                            if not value:
                                return default
                            value_str = str(value).strip().upper()
                            if value_str in ['NA', 'N/A', 'NULL']:
                                return default
                            if value_str == '':
                                return None  # Return None for empty strings
                            try:
                                int_value = int(value_str)
                                if int_value == 999:
                                    return None  # 999 is missing data in social science coding
                                return int_value
                            except ValueError:
                                return default
                        
                        # Create entries for each year found
                        logger.debug(f"Row {row_num}: Creating entries for {len(year_columns)} years")
                        for year, year_data in year_columns.items():
                            logger.debug(f"Row {row_num}: Processing year {year} with data: {year_data}")
                            try:
                                # Map field names to DataEntry fields
                                usage_code1 = year_data.get('NUTZUNG', 0)
                                usage_code2 = year_data.get('NUTZUNG_POLY1', 0)
                                usage_code3 = year_data.get('NUTZUNG_POLY2', 0)
                                cat_inno = year_data.get('CAT_INNO', 0)
                                cat_wert = year_data.get('CAT_WERT', 0)
                                cat_fili = year_data.get('CAT_FILI', 0)
                                nutzung_name = year_data.get('NUTZUNG_NAME', '').strip()
                                
                                # Convert to integers safely, treating 'NA' as 0, empty strings as None
                                usage_code1 = safe_int_convert(usage_code1, 0)
                                usage_code2 = safe_int_convert(usage_code2, 0)
                                usage_code3 = safe_int_convert(usage_code3, 0)
                                cat_inno = safe_int_convert(cat_inno, 0)
                                cat_wert = safe_int_convert(cat_wert, 0)
                                cat_fili = safe_int_convert(cat_fili, 0)
                                
                                # Use NUTZUNG_NAME if available, otherwise leave empty
                                entry_name = nutzung_name if nutzung_name else ""
                                
                                # Only create entry if at least one field has a non-None value
                                if any(val is not None for val in [usage_code1, usage_code2, usage_code3, cat_inno, cat_wert, cat_fili]):
                                    # Replace None values with 0 for database storage
                                    DataEntry.objects.create(
                                        geometry=geometry,
                                        name=entry_name,
                                        usage_code1=usage_code1 if usage_code1 is not None else 0,
                                        usage_code2=usage_code2 if usage_code2 is not None else 0,
                                        usage_code3=usage_code3 if usage_code3 is not None else 0,
                                        cat_inno=cat_inno if cat_inno is not None else 0,
                                        cat_wert=cat_wert if cat_wert is not None else 0,
                                        cat_fili=cat_fili if cat_fili is not None else 0,
                                        year=year,
                                        user=request.user
                                    )
                                    entries_created += 1
                                    import_summary['entries_created'] += 1
                                
                            except (ValueError, TypeError) as e:
                                # If data conversion fails for this year, skip this entry
                                errors.append(f"Row {row_num}: Invalid data for year {year} - {str(e)}")
                                continue
                        
                        # If no year-specific data exists, try to create entry with generic data
                        if entries_created == 0:
                            # Fallback to generic data if available
                            usage_code1 = row.get('NUTZUNG')
                            usage_code2 = row.get('NUTZUNG_POLY1')
                            usage_code3 = row.get('NUTZUNG_POLY2')
                            cat_inno = row.get('CAT_INNO')
                            cat_wert = row.get('CAT_WERT')
                            cat_fili = row.get('CAT_FILI')
                            year = row.get('YEAR')
                            nutzung_name = row.get('NUTZUNG_NAME', '').strip()
                            
                            # Convert to integers safely, treating 'NA' as 0, empty strings as None
                            usage_code1 = safe_int_convert(usage_code1, 0)
                            usage_code2 = safe_int_convert(usage_code2, 0)
                            usage_code3 = safe_int_convert(usage_code3, 0)
                            cat_inno = safe_int_convert(cat_inno, 0)
                            cat_wert = safe_int_convert(cat_wert, 0)
                            cat_fili = safe_int_convert(cat_fili, 0)
                            year = safe_int_convert(year, 2022)
                            
                            # Use NUTZUNG_NAME if available, otherwise leave empty
                            entry_name = nutzung_name if nutzung_name else ""
                            
                            # Only create entry if at least one field has a non-None value
                            if any(val is not None for val in [usage_code1, usage_code2, usage_code3, cat_inno, cat_wert, cat_fili]):
                                try:
                                    # Replace None values with 0 for database storage
                                    DataEntry.objects.create(
                                        geometry=geometry,
                                        name=entry_name,
                                        usage_code1=usage_code1 if usage_code1 is not None else 0,
                                        usage_code2=usage_code2 if usage_code2 is not None else 0,
                                        usage_code3=usage_code3 if usage_code3 is not None else 0,
                                        cat_inno=cat_inno if cat_inno is not None else 0,
                                        cat_wert=cat_wert if cat_wert is not None else 0,
                                        cat_fili=cat_fili if cat_fili is not None else 0,
                                        year=year,
                                        user=request.user
                                    )
                                    entries_created += 1
                                    import_summary['entries_created'] += 1
                                    
                                except ValueError:
                                    # If generic data conversion fails, skip this entry
                                    pass
                        
                        imported_count += 1
                        import_summary['rows_processed'] += 1
                        logger.debug(f"Row {row_num}: Successfully processed")
                        
                    except Exception as e:
                        logger.error(f"Row {row_num}: Unexpected error: {str(e)}")
                        errors.append(f"Row {row_num}: {str(e)}")
                        import_summary['rows_skipped'] += 1
                        continue
            
            logger.info(f"Import completed. Total rows processed: {row_count}, imported: {imported_count}, errors: {len(errors)}")
            
            # Log the import action
            AuditLog.objects.create(
                user=request.user,
                action='csv_import',
                target=f'dataset:{dataset.id} - Imported {imported_count} records'
            )
            
            # Calculate total counts for the dataset
            total_geometries = DataGeometry.objects.filter(dataset=dataset).count()
            total_entries = DataEntry.objects.filter(geometry__dataset=dataset).count()
            
            # Ensure import_summary exists
            if 'import_summary' not in locals():
                import_summary = {
                    'coordinate_system': 4326,
                    'coordinate_system_name': 'WGS84 (Latitude/Longitude)',
                    'detection_method': 'auto',
                    'geometries_created': 0,
                    'entries_created': 0,
                    'rows_processed': 0,
                    'rows_skipped': 0,
                    'transformation_errors': 0
                }
            
            # Always show import summary page if there are errors or if data was imported
            if errors or imported_count > 0:
                return render(request, 'frontend/import_summary.html', {
                    'dataset': dataset,
                    'import_summary': import_summary,
                    'errors': errors,
                    'total_geometries': total_geometries,
                    'total_entries': total_entries
                })
            
            # If no data was imported and no errors, redirect to dataset detail with error
            messages.error(request, 'No data was imported. Please check your CSV file format.')
            return redirect('dataset_detail', dataset_id=dataset.id)
            
        except Exception as e:
            logger.error(f"Critical error during CSV import: {str(e)}", exc_info=True)
            messages.error(request, f'Error processing CSV file: {str(e)}')
            return render(request, 'frontend/dataset_csv_import.html', {'dataset': dataset})
    
    return render(request, 'frontend/dataset_csv_import.html', {'dataset': dataset})

@login_required
def import_summary_view(request, dataset_id):
    """Display import summary for a dataset"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return HttpResponseForbidden("You do not have permission to view this dataset.")
    
    # Calculate current dataset statistics
    total_geometries = DataGeometry.objects.filter(dataset=dataset).count()
    total_entries = DataEntry.objects.filter(geometry__dataset=dataset).count()
    
    return render(request, 'frontend/import_summary.html', {
        'dataset': dataset,
        'total_geometries': total_geometries,
        'total_entries': total_entries,
        'import_summary': None,  # No import data available
        'errors': []
    })

@login_required
def debug_import_view(request, dataset_id):
    """Debug view to test CSV import with sample data"""
    if not request.user.is_superuser:
        return HttpResponseForbidden("Debug view only available to superusers")
    
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    if request.method == 'POST':
        # Create a sample CSV for testing
        sample_csv = """ID,ADRESSE,GEB_X,GEB_Y,2016_NUTZUNG,2016_CAT_INNO,2016_CAT_WERT,2016_CAT_FILI,2022_NUTZUNG,2022_CAT_INNO,2022_CAT_WERT,2022_CAT_FILI
test_001,Test Address 1,656610,3399131,870,999,999,999,870,999,999,999
test_002,Test Address 2,636410,3399724,640,0,0,0,640,0,0,0"""
        
        # Create a mock file object
        from django.core.files.base import ContentFile
        csv_file = ContentFile(sample_csv.encode('utf-8'), name='test_import.csv')
        
        # Mock the request.FILES
        request.FILES = {'csv_file': csv_file}
        request.POST = request.POST.copy()
        request.POST['coordinate_system'] = 'auto'
        
        logger.info("Starting debug import with sample CSV")
        
        # Call the actual import function
        return dataset_csv_import_view(request, dataset_id)
    
    return render(request, 'frontend/debug_import.html', {'dataset': dataset})

@login_required
def dataset_export_options_view(request, dataset_id):
    """Show export options for a dataset"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return HttpResponseForbidden("You do not have permission to export this dataset.")
    
    # Get dataset statistics
    geometries_count = DataGeometry.objects.filter(dataset=dataset).count()
    data_entries_count = DataEntry.objects.filter(geometry__dataset=dataset).count()
    
    # Get all unique years from entries
    years = set()
    geometries = DataGeometry.objects.filter(dataset=dataset)
    for geometry in geometries:
        for entry in geometry.entries.all():
            if entry.year:
                years.add(entry.year)
    
    years = sorted(list(years))
    
    return render(request, 'frontend/dataset_export.html', {
        'dataset': dataset,
        'geometries_count': geometries_count,
        'data_entries_count': data_entries_count,
        'years': years
    })

@login_required
def dataset_csv_export_view(request, dataset_id):
    """Export dataset as CSV with each geometry as a row and entries as columns named by years"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return HttpResponseForbidden("You do not have permission to export this dataset.")
    
    # Get all geometries for this dataset
    geometries = DataGeometry.objects.filter(dataset=dataset).order_by('id_kurz')
    
    if not geometries.exists():
        messages.warning(request, 'No data found to export.')
        return redirect('dataset_detail', dataset_id=dataset.id)
    
    # Get export parameters from request
    include_coordinates = request.GET.get('include_coordinates', 'true').lower() == 'true'
    include_empty_years = request.GET.get('include_empty_years', 'true').lower() == 'true'
    
    # Get all unique years from entries
    years = set()
    for geometry in geometries:
        for entry in geometry.entries.all():
            if entry.year:
                years.add(entry.year)
    
    years = sorted(list(years))
    
    # Define the fields to export for each year
    year_fields = [
        'usage_code1', 'usage_code2', 'usage_code3', 'cat_inno', 'cat_wert', 'cat_fili'
    ]
    
    # Create CSV response
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{dataset.name}_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header row
    header = ['ID', 'ADRESSE']
    if include_coordinates:
        header.extend(['GEB_X', 'GEB_Y'])
    
    for year in years:
        for field in year_fields:
            # Map field names to more readable column names
            field_mapping = {
                'usage_code1': 'USAGE_CODE1',
                'usage_code2': 'USAGE_CODE2', 
                'usage_code3': 'USAGE_CODE3',
                'cat_inno': 'CAT_INNO',
                'cat_wert': 'CAT_WERT',
                'cat_fili': 'CAT_FILI'
            }
            header.append(f'{year}_{field_mapping.get(field, field.upper())}')
    
    writer.writerow(header)
    
    # Write data rows
    for geometry in geometries:
        row = [
            geometry.id_kurz,
            geometry.address
        ]
        
        if include_coordinates:
            row.extend([
                geometry.geometry.x if geometry.geometry else '',
                geometry.geometry.y if geometry.geometry else ''
            ])
        
        # Add data for each year
        for year in years:
            # Get entry for this year (assuming one entry per year per geometry)
            entry = geometry.entries.filter(year=year).first()
            
            for field in year_fields:
                if entry:
                    value = getattr(entry, field, '')
                    # Convert None to empty string
                    row.append('' if value is None else str(value))
                else:
                    row.append('')
        
        writer.writerow(row)
    
    # Log the export action
    AuditLog.objects.create(
        user=request.user,
        action='csv_export',
        target=f'dataset:{dataset.id} - Exported {geometries.count()} geometries with {len(years)} years'
    )
    
    # Add success message
    messages.success(request, f'Successfully exported {geometries.count()} geometries with data from {len(years)} years.')
    
    return response


@login_required
def typology_create_view(request):
    """Create a new typology"""
    if request.method == 'POST':
        name = request.POST.get('name')
        if not name:
            messages.error(request, 'Typology name is required.')
            return render(request, 'frontend/typology_create.html', {'form': {'name': {'errors': ['This field is required.']}}})
        
        # Create the typology
        typology = Typology.objects.create(
            name=name,
            created_by=request.user
        )
        
        # Process typology entries
        entry_count = 0
        for key, value in request.POST.items():
            if key.startswith('entry_code_'):
                entry_count += 1
                code = request.POST.get(f'entry_code_{entry_count}')
                category = request.POST.get(f'entry_category_{entry_count}')
                name_entry = request.POST.get(f'entry_name_{entry_count}')
                
                if code and category and name_entry:
                    try:
                        TypologyEntry.objects.create(
                            typology=typology,
                            code=int(code),
                            category=category,
                            name=name_entry
                        )
                    except ValueError:
                        messages.error(request, f'Invalid code value: {code}')
                        typology.delete()
                        return render(request, 'frontend/typology_create.html', {'form': {'name': {'value': name}}})
                    except IntegrityError:
                        messages.error(request, f'Code {code} already exists in this typology.')
                        typology.delete()
                        return render(request, 'frontend/typology_create.html', {'form': {'name': {'value': name}}})
        
        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='typology_create',
            target=f'typology:{typology.id} - {typology.name}'
        )
        
        messages.success(request, f'Typology "{typology.name}" created successfully with {entry_count} entries.')
        
        # If dataset_id was provided, assign the typology to that dataset
        dataset_id = request.GET.get('dataset_id')
        if dataset_id:
            try:
                dataset = DataSet.objects.get(id=dataset_id, owner=request.user)
                dataset.typology = typology
                dataset.save()
                messages.success(request, f'Typology assigned to dataset "{dataset.name}".')
                return redirect('dataset_detail', dataset_id=dataset.id)
            except DataSet.DoesNotExist:
                pass
        
        return redirect('typology_list')
    
    return render(request, 'frontend/typology_create.html', {'dataset_id': request.GET.get('dataset_id')})


@login_required
def typology_edit_view(request, typology_id):
    """Edit an existing typology"""
    typology = get_object_or_404(Typology, id=typology_id)
    
    # Check if user has permission to edit this typology
    if typology.created_by != request.user:
        messages.error(request, 'You do not have permission to edit this typology.')
        return redirect('dataset_list')
    
    if request.method == 'POST':
        # Update typology name
        name = request.POST.get('name')
        if name and name != typology.name:
            typology.name = name
            typology.save()
        
        # Update existing entries
        for entry in typology.entries.all():
            code = request.POST.get(f'entry_code_{entry.id}')
            category = request.POST.get(f'entry_category_{entry.id}')
            name_entry = request.POST.get(f'entry_name_{entry.id}')
            
            if code and category and name_entry:
                try:
                    entry.code = int(code)
                    entry.category = category
                    entry.name = name_entry
                    entry.save()
                except ValueError:
                    messages.error(request, f'Invalid code value: {code}')
                    return render(request, 'frontend/typology_edit.html', {'typology': typology})
                except IntegrityError:
                    messages.error(request, f'Code {code} already exists in this typology.')
                    return render(request, 'frontend/typology_edit.html', {'typology': typology})
        
        # Add new entries
        new_entry_count = 0
        for key, value in request.POST.items():
            if key.startswith('new_entry_code_'):
                new_entry_count += 1
                code = request.POST.get(f'new_entry_code_{new_entry_count}')
                category = request.POST.get(f'new_entry_category_{new_entry_count}')
                name_entry = request.POST.get(f'new_entry_name_{new_entry_count}')
                
                if code and category and name_entry:
                    try:
                        TypologyEntry.objects.create(
                            typology=typology,
                            code=int(code),
                            category=category,
                            name=name_entry
                        )
                    except ValueError:
                        messages.error(request, f'Invalid code value: {code}')
                        return render(request, 'frontend/typology_edit.html', {'typology': typology})
                    except IntegrityError:
                        messages.error(request, f'Code {code} already exists in this typology.')
                        return render(request, 'frontend/typology_edit.html', {'typology': typology})
        
        # Delete entries marked for deletion
        delete_entries = request.POST.getlist('delete_entry')
        for entry_id in delete_entries:
            try:
                entry = TypologyEntry.objects.get(id=entry_id, typology=typology)
                entry.delete()
            except TypologyEntry.DoesNotExist:
                pass
        
        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='typology_edit',
            target=f'typology:{typology.id} - {typology.name}'
        )
        
        messages.success(request, f'Typology "{typology.name}" updated successfully.')
        
        # Redirect back to dataset if dataset_id was provided
        dataset_id = request.GET.get('dataset_id')
        if dataset_id:
            return redirect('dataset_detail', dataset_id=dataset_id)
        
        return redirect('typology_list')
    
    return render(request, 'frontend/typology_edit.html', {'typology': typology})


@login_required
def typology_select_view(request, dataset_id):
    """Select an existing typology for a dataset"""
    dataset = get_object_or_404(DataSet, id=dataset_id, owner=request.user)
    
    if request.method == 'POST':
        typology_id = request.POST.get('typology_id')
        if typology_id:
            try:
                typology = Typology.objects.get(id=typology_id)
                dataset.typology = typology
                dataset.save()
                
                # Log the action
                AuditLog.objects.create(
                    user=request.user,
                    action='typology_assign',
                    target=f'dataset:{dataset.id} assigned typology:{typology.id}'
                )
                
                messages.success(request, f'Typology "{typology.name}" assigned to dataset "{dataset.name}".')
                return redirect('dataset_detail', dataset_id=dataset.id)
            except Typology.DoesNotExist:
                messages.error(request, 'Selected typology does not exist.')
    
    # Get all typologies
    typologies = Typology.objects.all().order_by('-created_at')
    
    # Get dataset statistics
    geometries_count = DataGeometry.objects.filter(dataset=dataset).count()
    data_entries_count = DataEntry.objects.filter(geometry__dataset=dataset).count()
    
    return render(request, 'frontend/typology_select.html', {
        'dataset': dataset,
        'typologies': typologies,
        'geometries_count': geometries_count,
        'data_entries_count': data_entries_count
    })


@login_required
def typology_list_view(request):
    """List all typologies"""
    typologies = Typology.objects.all().order_by('-created_at')
    
    return render(request, 'frontend/typology_list.html', {
        'typologies': typologies
    })


@login_required
def typology_import_view(request, typology_id):
    """Import typology entries from CSV"""
    typology = get_object_or_404(Typology, id=typology_id)
    
    # Check if user has permission to edit this typology
    if typology.created_by != request.user:
        messages.error(request, 'You do not have permission to edit this typology.')
        return redirect('dataset_list')
    
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        skip_header = request.POST.get('skip_header') == 'on'
        update_existing = request.POST.get('update_existing') == 'on'
        
        if not csv_file:
            messages.error(request, 'Please select a CSV file.')
            return render(request, 'frontend/typology_import.html', {'typology': typology})
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a valid CSV file.')
            return render(request, 'frontend/typology_import.html', {'typology': typology})
        
        try:
            # Read CSV file
            decoded_file = csv_file.read().decode('utf-8')
            csv_data = csv.reader(io.StringIO(decoded_file))
            
            # Skip header if requested
            if skip_header:
                next(csv_data, None)
            
            # Process rows
            imported_count = 0
            updated_count = 0
            error_count = 0
            errors = []
            
            for row_num, row in enumerate(csv_data, 1):
                if len(row) < 3:
                    errors.append(f"Row {row_num}: Insufficient columns (expected 3, got {len(row)})")
                    error_count += 1
                    continue
                
                code_str, category, name = row[:3]
                
                # Validate code
                try:
                    code = int(code_str.strip())
                except ValueError:
                    errors.append(f"Row {row_num}: Invalid code '{code_str}' (must be integer)")
                    error_count += 1
                    continue
                
                # Validate other fields
                if not category.strip():
                    errors.append(f"Row {row_num}: Category cannot be empty")
                    error_count += 1
                    continue
                
                if not name.strip():
                    errors.append(f"Row {row_num}: Name cannot be empty")
                    error_count += 1
                    continue
                
                # Check if entry already exists
                existing_entry = TypologyEntry.objects.filter(typology=typology, code=code).first()
                
                if existing_entry:
                    if update_existing:
                        # Update existing entry
                        existing_entry.category = category.strip()
                        existing_entry.name = name.strip()
                        existing_entry.save()
                        updated_count += 1
                    else:
                        errors.append(f"Row {row_num}: Code {code} already exists")
                        error_count += 1
                else:
                    # Create new entry
                    try:
                        TypologyEntry.objects.create(
                            typology=typology,
                            code=code,
                            category=category.strip(),
                            name=name.strip()
                        )
                        imported_count += 1
                    except IntegrityError:
                        errors.append(f"Row {row_num}: Code {code} already exists")
                        error_count += 1
            
            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action='typology_import',
                target=f'typology:{typology.id} - Imported {imported_count} entries, updated {updated_count} entries'
            )
            
            # Show results
            if imported_count > 0 or updated_count > 0:
                success_msg = f'Successfully imported {imported_count} new entries'
                if updated_count > 0:
                    success_msg += f' and updated {updated_count} existing entries'
                success_msg += f' to typology "{typology.name}".'
                messages.success(request, success_msg)
            
            if error_count > 0:
                error_msg = f'Failed to import {error_count} entries due to errors.'
                if errors:
                    error_msg += ' First few errors: ' + '; '.join(errors[:5])
                messages.warning(request, error_msg)
            
            return redirect('typology_edit', typology_id=typology.id)
            
        except UnicodeDecodeError:
            messages.error(request, 'The CSV file contains invalid characters. Please ensure it is UTF-8 encoded.')
            return render(request, 'frontend/typology_import.html', {'typology': typology})
        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')
            return render(request, 'frontend/typology_import.html', {'typology': typology})
    
    return render(request, 'frontend/typology_import.html', {'typology': typology})


@login_required
def typology_export_view(request, typology_id):
    """Export typology entries to CSV"""
    typology = get_object_or_404(Typology, id=typology_id)
    
    # Check if user has access to this typology
    if typology.created_by != request.user:
        messages.error(request, 'You do not have permission to export this typology.')
        return redirect('dataset_list')
    
    if request.method == 'POST':
        filename = request.POST.get('filename', f'{typology.name}_entries')
        include_header = request.POST.get('include_header') == 'on'
        sort_by = request.POST.get('sort_by', 'code')
        
        # Clean filename
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not filename:
            filename = f'{typology.name}_entries'
        
        # Get entries with sorting
        if sort_by == 'code':
            entries = typology.entries.all().order_by('code')
        elif sort_by == 'category':
            entries = typology.entries.all().order_by('category', 'code')
        elif sort_by == 'name':
            entries = typology.entries.all().order_by('name', 'code')
        else:
            entries = typology.entries.all().order_by('code')
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        
        writer = csv.writer(response)
        
        # Write header if requested
        if include_header:
            writer.writerow(['code', 'category', 'name'])
        
        # Write data rows
        for entry in entries:
            writer.writerow([entry.code, entry.category, entry.name])
        
        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='typology_export',
            target=f'typology:{typology.id} - Exported {entries.count()} entries'
        )
        
        return response
    
    return render(request, 'frontend/typology_export.html', {'typology': typology})