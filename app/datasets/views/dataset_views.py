from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q

from ..models import DataSet, DataGeometry, DataEntry, DataEntryField, DatasetField, AuditLog, Typology
from ..forms import DatasetFieldConfigForm, DatasetFieldForm, TransferOwnershipForm
def _get_typology_categories_map():
    categories = {}
    typologies = Typology.objects.all().order_by('name')
    for typology in typologies:
        category_values = (
            typology.entries.order_by('category')
            .values_list('category', flat=True)
            .distinct()
        )
        categories[str(typology.id)] = [value for value in category_values if value]
    return categories
from .auth_views import is_manager


@login_required
def dataset_list_view(request):
    """List all datasets accessible to the user"""
    # Superusers can see all datasets regardless of access permissions
    if request.user.is_superuser:
        all_datasets = DataSet.objects.all().order_by('-created_at')
    else:
        # Get datasets owned by user or shared with user
        owned_datasets = DataSet.objects.filter(owner=request.user)
        shared_datasets = DataSet.objects.filter(shared_with=request.user)
        group_shared_datasets = DataSet.objects.filter(shared_with_groups__in=request.user.groups.all())
        public_datasets = DataSet.objects.filter(is_public=True)
        
        # Combine and deduplicate
        all_datasets = (owned_datasets | shared_datasets | group_shared_datasets | public_datasets).distinct()
    
    return render(request, 'datasets/dataset_list.html', {
        'datasets': all_datasets,
        'can_create_datasets': is_manager(request.user)
    })


@login_required
def dataset_create_view(request):
    """Create a new dataset"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        if name:
            dataset = DataSet.objects.create(
                name=name,
                description=description,
                owner=request.user
            )
            messages.success(request, f'Dataset "{name}" created successfully!')
            return redirect('dataset_detail', dataset_id=dataset.id)
        else:
            messages.error(request, 'Dataset name is required.')
    
    return render(request, 'datasets/dataset_create.html')


@login_required
def dataset_detail_view(request, dataset_id):
    """View dataset details and manage fields"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    # Handle field configuration updates
    if request.method == 'POST' and request.POST.get('action') == 'update_fields':
        if dataset.owner == request.user:
            try:
                # Update field configurations
                for field in DatasetField.objects.filter(dataset=dataset):
                    field_id = field.id
                    
                    # Update label
                    if f'field_{field_id}_label' in request.POST:
                        field.label = request.POST[f'field_{field_id}_label']
                    
                    # Update order
                    if f'field_{field_id}_order' in request.POST:
                        try:
                            field.order = int(request.POST[f'field_{field_id}_order'])
                        except ValueError:
                            pass
                    
                    # Update enabled status
                    field.enabled = f'field_{field_id}_enabled' in request.POST
                    
                    # Update required status
                    field.required = f'field_{field_id}_required' in request.POST
                    
                    field.save()
                
                messages.success(request, 'Field configuration updated successfully.')
            except Exception as e:
                messages.error(request, f'Error updating field configuration: {str(e)}')
        
        return redirect('dataset_detail', dataset_id=dataset.id)
    
    # Get counts for geometries and data entries
    geometries_count = DataGeometry.objects.filter(dataset=dataset).count()
    data_entries_count = DataEntry.objects.filter(geometry__dataset=dataset).count()
    
    # Get all fields for this dataset
    all_fields = DatasetField.objects.filter(dataset=dataset).order_by('order', 'field_name')
    
    return render(request, 'datasets/dataset_detail.html', {
        'dataset': dataset,
        'geometries_count': geometries_count,
        'data_entries_count': data_entries_count,
        'all_fields': all_fields
    })


@login_required
def dataset_edit_view(request, dataset_id):
    """Edit dataset details"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Only dataset owner can edit
    if dataset.owner != request.user:
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        if 'delete_dataset' in request.POST:
            # Handle dataset deletion
            dataset_name = dataset.name
            dataset.delete()
            messages.success(request, f'Dataset "{dataset_name}" deleted successfully!')
            return redirect('dataset_list')
        
        # Handle dataset update
        name = request.POST.get('name')
        description = request.POST.get('description')
        is_public = request.POST.get('is_public') == 'on'
        allow_multiple_entries = request.POST.get('allow_multiple_entries') == 'on'
        
        if name:
            dataset.name = name
            dataset.description = description
            dataset.is_public = is_public
            # Handle allow_multiple_entries field (graceful handling for migration)
            try:
                dataset.allow_multiple_entries = allow_multiple_entries
            except AttributeError:
                pass  # Field doesn't exist yet, skip
            dataset.save()
            
            messages.success(request, 'Dataset updated successfully!')
            return redirect('dataset_detail', dataset_id=dataset.id)
        else:
            messages.error(request, 'Dataset name is required.')
    
    return render(request, 'datasets/dataset_edit.html', {
        'dataset': dataset,
        'geometries_count': DataGeometry.objects.filter(dataset=dataset).count(),
        'entries_count': DataEntry.objects.filter(geometry__dataset=dataset).count(),
        'field_count': DatasetField.objects.filter(dataset=dataset).count()
    })


@login_required
def dataset_access_view(request, dataset_id):
    """Manage dataset access permissions"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Only dataset owner can manage access
    if dataset.owner != request.user:
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        # Handle bulk user access changes
        selected_user_ids = request.POST.getlist('shared_users')
        selected_group_ids = request.POST.getlist('shared_groups')
        
        # Convert to integers
        selected_user_ids = [int(uid) for uid in selected_user_ids if uid.isdigit()]
        selected_group_ids = [int(gid) for gid in selected_group_ids if gid.isdigit()]
        
        # Update user access
        current_user_ids = set(dataset.shared_with.values_list('id', flat=True))
        new_user_ids = set(selected_user_ids)
        
        # Add new users
        users_to_add = new_user_ids - current_user_ids
        if users_to_add:
            users_to_add_objects = User.objects.filter(id__in=users_to_add)
            dataset.shared_with.add(*users_to_add_objects)
            messages.success(request, f'Added {len(users_to_add_objects)} users to dataset access.')
        
        # Remove users
        users_to_remove = current_user_ids - new_user_ids
        if users_to_remove:
            users_to_remove_objects = User.objects.filter(id__in=users_to_remove)
            dataset.shared_with.remove(*users_to_remove_objects)
            messages.success(request, f'Removed {len(users_to_remove_objects)} users from dataset access.')
        
        # Update group access
        current_group_ids = set(dataset.shared_with_groups.values_list('id', flat=True))
        new_group_ids = set(selected_group_ids)
        
        # Add new groups
        groups_to_add = new_group_ids - current_group_ids
        if groups_to_add:
            groups_to_add_objects = Group.objects.filter(id__in=groups_to_add)
            dataset.shared_with_groups.add(*groups_to_add_objects)
            messages.success(request, f'Added {len(groups_to_add_objects)} groups to dataset access.')
        
        # Remove groups
        groups_to_remove = current_group_ids - new_group_ids
        if groups_to_remove:
            groups_to_remove_objects = Group.objects.filter(id__in=groups_to_remove)
            dataset.shared_with_groups.remove(*groups_to_remove_objects)
            messages.success(request, f'Removed {len(groups_to_remove_objects)} groups from dataset access.')
        
        # If no changes were made
        if not (users_to_add or users_to_remove or groups_to_add or groups_to_remove):
            messages.info(request, 'No changes were made to access settings.')
        
        return redirect('dataset_access', dataset_id=dataset.id)
    
    # Get all users and groups for selection
    all_users = User.objects.all().exclude(id=dataset.owner.id)
    all_groups = Group.objects.all()
    
    # Get currently shared users and groups
    shared_users = list(dataset.shared_with.values_list('id', flat=True))
    shared_groups = list(dataset.shared_with_groups.values_list('id', flat=True))
    
    return render(request, 'datasets/dataset_access.html', {
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
        return render(request, 'datasets/403.html', status=403)
    
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
            entry_data = {
                'id': entry.id,
                'name': entry.name,
                'year': entry.year,
                'user': entry.user.username if entry.user else 'Unknown'
            }
            
            # Add dynamic field values
            for field in entry.fields.all():
                entry_data[field.field_name] = field.get_typed_value()
            
            map_point['entries'].append(entry_data)
        
        map_data.append(map_point)
    
    # Typology data is now handled at the field level, not dataset level
    typology_data = None
    
    # Get all enabled fields for this dataset (both standard and custom)
    all_fields = DatasetField.objects.filter(dataset=dataset, enabled=True).order_by('order', 'field_name')
    
    # If no enabled fields found, get all fields and enable them
    if not all_fields.exists():
        all_fields_qs = DatasetField.objects.filter(dataset=dataset)
        if all_fields_qs.exists():
            # Enable all fields
            all_fields_qs.update(enabled=True)
            # Re-query to get the updated fields
            all_fields = DatasetField.objects.filter(dataset=dataset, enabled=True).order_by('order', 'field_name')
    
    # Prepare fields data for JavaScript with typology choices
    fields_data = []
    for field in all_fields:
        field_data = {
            'id': field.id,
            'name': field.label,  # Use label for display
            'label': field.label,
            'field_type': 'choice' if field.typology else field.field_type,
            'field_name': field.field_name,
            'required': field.required,
            'enabled': field.enabled,
            'help_text': field.help_text or '',
            'choices': field.choices or '',
            'order': field.order,
            'typology_choices': field.get_choices_list() if field.typology else [],
            'typology_category': field.typology_category or ''
        }
        fields_data.append(field_data)
    
    # Handle case where allow_multiple_entries field might not exist yet (migration not applied)
    try:
        allow_multiple_entries = dataset.allow_multiple_entries
    except AttributeError:
        allow_multiple_entries = False  # Default to False if field doesn't exist
    
    return render(request, 'datasets/dataset_data_input.html', {
        'dataset': dataset,
        'geometries': geometries,
        'typology_data': typology_data,
        'all_fields': all_fields,
        'fields_data': fields_data,
        'allow_multiple_entries': allow_multiple_entries
    })


@login_required
def dataset_entries_table_view(request, dataset_id):
    """Display all dataset entries in a table format"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    # Get all entries for this dataset
    entries = DataEntry.objects.filter(geometry__dataset=dataset).select_related('geometry', 'user').prefetch_related('fields')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        entries = entries.filter(
            Q(name__icontains=search_query) |
            Q(geometry__id_kurz__icontains=search_query) |
            Q(geometry__address__icontains=search_query)
        )
    
    # Sorting
    sort_by = request.GET.get('sort', 'name')
    reverse = request.GET.get('order', 'asc') == 'desc'
    
    if sort_by == 'geometry':
        entries = entries.order_by('geometry__id_kurz')
    elif sort_by == 'year':
        entries = entries.order_by('year')
    elif sort_by == 'user':
        entries = entries.order_by('user__username')
    else:
        entries = entries.order_by('name')
    
    if reverse:
        entries = entries.reverse()
    
    # Pagination
    paginator = Paginator(entries, 25)  # Show 25 entries per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'datasets/dataset_entries_table.html', {
        'dataset': dataset,
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
        'order': 'desc' if reverse else 'asc'
    })


@login_required
def dataset_fields_view(request, dataset_id):
    """API endpoint to get dataset fields"""
    try:
        dataset = get_object_or_404(DataSet, pk=dataset_id)
        if not dataset.can_access(request.user):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Get all enabled fields for this dataset
        all_fields = DatasetField.objects.filter(dataset=dataset, enabled=True).order_by('order', 'field_name')
        
        # If no enabled fields found, get all fields and enable them
        if not all_fields.exists():
            all_fields_qs = DatasetField.objects.filter(dataset=dataset)
            if all_fields_qs.exists():
                # Enable all fields
                all_fields_qs.update(enabled=True)
                # Re-query to get the updated fields
                all_fields = DatasetField.objects.filter(dataset=dataset, enabled=True).order_by('order', 'field_name')
        
        # Prepare fields data for JavaScript
        fields_data = []
        for field in all_fields:
            field_data = {
                'id': field.id,
                'name': field.label,
                'label': field.label,
                'field_type': 'choice' if field.typology else field.field_type,
                'field_name': field.field_name,
                'required': field.required,
                'enabled': field.enabled,
                'help_text': field.help_text or '',
                'choices': field.choices or '',
                'order': field.order,
                'typology_choices': field.get_choices_list() if field.typology else [],
                'typology_category': field.typology_category or ''
            }
            fields_data.append(field_data)
        
        return JsonResponse({'fields': fields_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def dataset_map_data_view(request, dataset_id):
    """API endpoint to get lightweight map data for a dataset (coordinates only)"""
    try:
        dataset = get_object_or_404(DataSet, pk=dataset_id)
        if not dataset.can_access(request.user):
            return render(request, 'datasets/403.html', status=403)
        
        # Get map bounds from request parameters
        bounds = request.GET.get('bounds')
        
        if bounds:
            try:
                # Parse bounds: "south,west,north,east"
                south, west, north, east = map(float, bounds.split(','))
                
                # Filter geometries within the bounds using spatial lookups
                from django.contrib.gis.geos import Polygon
                
                # Create a bounding box polygon
                bbox = Polygon.from_bbox((west, south, east, north))
                
                # Filter geometries within the bounds (lightweight query)
                geometries = DataGeometry.objects.filter(
                    dataset=dataset,
                    geometry__within=bbox
                ).only('id', 'id_kurz', 'address', 'geometry', 'user__username')
            except (ValueError, TypeError) as e:
                # If bounds parsing fails, get all geometries
                geometries = DataGeometry.objects.filter(dataset=dataset).only(
                    'id', 'id_kurz', 'address', 'geometry', 'user__username'
                )
        else:
            # No bounds provided, get all geometries (lightweight query)
            geometries = DataGeometry.objects.filter(dataset=dataset).only(
                'id', 'id_kurz', 'address', 'geometry', 'user__username'
            )
        
        # Prepare lightweight map data
        map_data = []
        for geometry in geometries:
            try:
                map_point = {
                    'id': geometry.id,
                    'id_kurz': geometry.id_kurz,
                    'address': geometry.address,
                    'lat': geometry.geometry.y,
                    'lng': geometry.geometry.x,
                    'user': geometry.user.username if geometry.user else 'Unknown'
                }
                map_data.append(map_point)
            except Exception as e:
                continue
        
        return JsonResponse({'map_data': map_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def dataset_clear_data_view(request, dataset_id):
    """Clear all geometry points and data entries from a dataset"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Only dataset owner can clear data
    if dataset.owner != request.user:
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        # Delete all geometries and their related data
        geometries_count = DataGeometry.objects.filter(dataset=dataset).count()
        DataGeometry.objects.filter(dataset=dataset).delete()
        
        messages.success(request, f'Cleared {geometries_count} geometry points and all related data from dataset "{dataset.name}".')
        return redirect('dataset_detail', dataset_id=dataset.id)
    
    return render(request, 'datasets/dataset_clear_data.html', {
        'dataset': dataset
    })


@login_required
def custom_field_create_view(request, dataset_id):
    """Create a new custom field for a dataset"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        form = DatasetFieldForm(request.POST)
        if form.is_valid():
            field = form.save(commit=False)
            field.dataset = dataset
            field.save()
            messages.success(request, f'Field "{field.label}" created successfully!')
            return redirect('dataset_detail', dataset_id=dataset.id)
        # Form is invalid - will be re-rendered with errors below
    else:
        form = DatasetFieldForm()
    
    return render(request, 'datasets/custom_field_form.html', {
        'dataset': dataset,
        'form': form,
        'title': 'Create Custom Field',
        'typology_categories': _get_typology_categories_map()
    })


@login_required
def custom_field_edit_view(request, dataset_id, field_id):
    """Edit a custom field for a dataset"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    field = get_object_or_404(DatasetField, id=field_id, dataset=dataset)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        form = DatasetFieldForm(request.POST, instance=field)
        if form.is_valid():
            form.save()
            messages.success(request, f'Field "{field.label}" updated successfully!')
            return redirect('dataset_detail', dataset_id=dataset.id)
        # Form is invalid - will be re-rendered with errors below
    else:
        form = DatasetFieldForm(instance=field)
    
    return render(request, 'datasets/custom_field_form.html', {
        'dataset': dataset,
        'field': field,
        'form': form,
        'title': 'Edit Custom Field',
        'typology_categories': _get_typology_categories_map()
    })


@login_required
def custom_field_delete_view(request, dataset_id, field_id):
    """Delete a custom field for a dataset"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    field = get_object_or_404(DatasetField, id=field_id, dataset=dataset)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        field_name = field.label
        field.delete()
        messages.success(request, f'Field "{field_name}" deleted successfully!')
        return redirect('dataset_detail', dataset_id=dataset.id)
    
    return render(request, 'datasets/custom_field_delete.html', {
        'dataset': dataset,
        'field': field
    })


@login_required
def dataset_transfer_ownership_view(request, dataset_id):
    """Transfer ownership of a dataset to another user"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Only the current owner can transfer ownership
    if dataset.owner != request.user:
        messages.error(request, 'You do not have permission to transfer ownership of this dataset.')
        return redirect('dataset_detail', dataset_id=dataset.id)
    
    if request.method == 'POST':
        form = TransferOwnershipForm(request.POST, current_owner=dataset.owner)
        if form.is_valid():
            new_owner = form.cleaned_data['new_owner']
            old_owner = dataset.owner
            
            # Transfer ownership
            dataset.owner = new_owner
            dataset.save()
            
            messages.success(request, f'Ownership of "{dataset.name}" has been transferred to {new_owner.username}.')
            return redirect('dataset_detail', dataset_id=dataset.id)
    else:
        form = TransferOwnershipForm(current_owner=dataset.owner)
    
    return render(request, 'datasets/dataset_transfer_ownership.html', {
        'dataset': dataset,
        'form': form
    })
