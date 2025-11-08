from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q

from ..models import (
    DataSet,
    DataGeometry,
    DataEntry,
    DataEntryField,
    DatasetField,
    DatasetFieldConfig,
    AuditLog,
    Typology,
    DatasetUserMappingArea,
    DatasetGroupMappingArea,
)
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


STANDARD_DATASET_FIELDS = [
    {
        'field_name': 'name',
        'config_label_attr': 'name_label',
        'config_enabled_attr': 'name_enabled',
        'field_type': 'text',
        'order': 0,
        'required': True,
        'help_text': 'Primary entry name shown in lists and reports.',
    },
    {
        'field_name': 'usage_code1',
        'config_label_attr': 'usage_code1_label',
        'config_enabled_attr': 'usage_code1_enabled',
        'field_type': 'integer',
        'order': 1,
        'help_text': 'First usage code column imported from legacy data.',
    },
    {
        'field_name': 'usage_code2',
        'config_label_attr': 'usage_code2_label',
        'config_enabled_attr': 'usage_code2_enabled',
        'field_type': 'integer',
        'order': 2,
    },
    {
        'field_name': 'usage_code3',
        'config_label_attr': 'usage_code3_label',
        'config_enabled_attr': 'usage_code3_enabled',
        'field_type': 'integer',
        'order': 3,
    },
    {
        'field_name': 'cat_inno',
        'config_label_attr': 'cat_inno_label',
        'config_enabled_attr': 'cat_inno_enabled',
        'field_type': 'integer',
        'order': 4,
    },
    {
        'field_name': 'cat_wert',
        'config_label_attr': 'cat_wert_label',
        'config_enabled_attr': 'cat_wert_enabled',
        'field_type': 'integer',
        'order': 5,
    },
    {
        'field_name': 'cat_fili',
        'config_label_attr': 'cat_fili_label',
        'config_enabled_attr': 'cat_fili_enabled',
        'field_type': 'integer',
        'order': 6,
    },
    {
        'field_name': 'year',
        'config_label_attr': 'year_label',
        'config_enabled_attr': 'year_enabled',
        'field_type': 'integer',
        'order': 7,
        'help_text': 'Reference year for the entry.',
    },
]


def ensure_dataset_field_config(dataset: DataSet) -> DatasetFieldConfig:
    """Ensure a DatasetFieldConfig instance exists for the dataset."""
    config, _ = DatasetFieldConfig.objects.get_or_create(dataset=dataset)
    return config


def ensure_standard_dataset_fields(dataset: DataSet) -> DatasetFieldConfig:
    """Create or update the standard dataset fields as defined in DatasetFieldConfig."""
    config = ensure_dataset_field_config(dataset)
    for field_def in STANDARD_DATASET_FIELDS:
        label = getattr(config, field_def['config_label_attr'], field_def['field_name'].replace('_', ' ').title())
        enabled = getattr(config, field_def['config_enabled_attr'], True)
        defaults = {
            'label': label,
            'field_type': field_def['field_type'],
            'required': field_def.get('required', False),
            'enabled': enabled,
            'order': field_def['order'],
            'help_text': field_def.get('help_text', ''),
        }
        field, created = DatasetField.objects.get_or_create(
            dataset=dataset,
            field_name=field_def['field_name'],
            defaults=defaults,
        )
        if not created:
            updated = False
            for attr, value in defaults.items():
                if getattr(field, attr) != value:
                    setattr(field, attr, value)
                    updated = True
            if updated:
                field.save()
    return config


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

    # Ensure standard field configuration exists
    ensure_standard_dataset_fields(dataset)
    
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
def dataset_field_config_view(request, dataset_id):
    """Manage standard dataset field configuration (labels, enabled flags)."""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    if dataset.owner != request.user:
        return render(request, 'datasets/403.html', status=403)
    
    config = ensure_standard_dataset_fields(dataset)
    form = DatasetFieldConfigForm(instance=config)
    
    if request.method == 'POST':
        config_field_names = set(DatasetFieldConfigForm.Meta.fields)
        config_fields_present = any(field_name in request.POST for field_name in config_field_names)
        
        form_valid = True
        if config_fields_present:
            form = DatasetFieldConfigForm(request.POST, instance=config)
            if form.is_valid():
                form.save()
                ensure_standard_dataset_fields(dataset)
            else:
                form_valid = False
        
        dataset_fields = DatasetField.objects.filter(dataset=dataset).order_by('order', 'field_name')
        dataset_fields_updated = False
        for field in dataset_fields:
            field_prefix = f'field_{field.id}'
            label_key = f'{field_prefix}_label'
            order_key = f'{field_prefix}_order'
            help_text_key = f'{field_prefix}_help_text'
            enabled_key = f'{field_prefix}_enabled'
            required_key = f'{field_prefix}_required'
            
            changed = False
            
            if label_key in request.POST:
                new_label = request.POST.get(label_key, '').strip()
                if new_label and new_label != field.label:
                    field.label = new_label
                    changed = True
            
            if order_key in request.POST:
                try:
                    new_order = int(request.POST[order_key])
                except (ValueError, TypeError):
                    new_order = field.order
                if new_order != field.order:
                    field.order = new_order
                    changed = True
            
            if help_text_key in request.POST:
                new_help_text = request.POST.get(help_text_key, '').strip()
                if new_help_text != (field.help_text or ''):
                    field.help_text = new_help_text
                    changed = True
            
            enabled_value = request.POST.get(enabled_key) == 'on'
            if enabled_value != field.enabled:
                field.enabled = enabled_value
                changed = True
            
            required_value = request.POST.get(required_key) == 'on'
            if required_value != field.required:
                field.required = required_value
                changed = True
            
            if changed:
                field.save()
                dataset_fields_updated = True
        
        if (config_fields_present and form_valid) or dataset_fields_updated:
            messages.success(request, 'Field configuration updated successfully.')
            return redirect('dataset_field_config', dataset_id=dataset.id)
        if config_fields_present and not form_valid:
            messages.error(request, 'Please correct the errors below.')
    
    all_fields = DatasetField.objects.filter(dataset=dataset).order_by('order', 'field_name')
    
    return render(request, 'datasets/dataset_field_config.html', {
        'dataset': dataset,
        'form': form,
        'all_fields': all_fields,
    })


@login_required
def dataset_access_view(request, dataset_id):
    """Manage dataset access permissions"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Only dataset owner can manage access
    if dataset.owner != request.user:
        return render(request, 'datasets/403.html', status=403)
    
    mapping_areas = list(dataset.mapping_areas.order_by('name'))
    
    if request.method == 'POST':
        # Handle bulk user access changes
        selected_user_ids = [
            int(uid) for uid in request.POST.getlist('shared_users') if uid.isdigit()
        ]
        selected_group_ids = [
            int(gid) for gid in request.POST.getlist('shared_groups') if gid.isdigit()
        ]
        selected_user_set = set(selected_user_ids)
        selected_group_set = set(selected_group_ids)
        
        # Update user access
        current_user_ids = set(dataset.shared_with.values_list('id', flat=True))
        # Add new users
        users_to_add = selected_user_set - current_user_ids
        if users_to_add:
            users_to_add_objects = User.objects.filter(id__in=users_to_add)
            dataset.shared_with.add(*users_to_add_objects)
            messages.success(request, f'Added {len(users_to_add_objects)} users to dataset access.')
        
        # Remove users
        users_to_remove = current_user_ids - selected_user_set
        if users_to_remove:
            users_to_remove_objects = User.objects.filter(id__in=users_to_remove)
            dataset.shared_with.remove(*users_to_remove_objects)
            messages.success(request, f'Removed {len(users_to_remove_objects)} users from dataset access.')
        
        # Update group access
        current_group_ids = set(dataset.shared_with_groups.values_list('id', flat=True))
        # Add new groups
        groups_to_add = selected_group_set - current_group_ids
        if groups_to_add:
            groups_to_add_objects = Group.objects.filter(id__in=groups_to_add)
            dataset.shared_with_groups.add(*groups_to_add_objects)
            messages.success(request, f'Added {len(groups_to_add_objects)} groups to dataset access.')
        
        # Remove groups
        groups_to_remove = current_group_ids - selected_group_set
        if groups_to_remove:
            groups_to_remove_objects = Group.objects.filter(id__in=groups_to_remove)
            dataset.shared_with_groups.remove(*groups_to_remove_objects)
            messages.success(request, f'Removed {len(groups_to_remove_objects)} groups from dataset access.')
        
        # If no changes were made
        # Handle mapping area restrictions
        if mapping_areas:
            valid_area_ids = set(area.id for area in mapping_areas)
            
            if selected_user_set:
                DatasetUserMappingArea.objects.filter(dataset=dataset).exclude(user_id__in=selected_user_set).delete()
            else:
                DatasetUserMappingArea.objects.filter(dataset=dataset).delete()
            
            for user_id in selected_user_ids:
                raw_area_ids = request.POST.getlist(f'user_mapping_areas_{user_id}')
                area_ids = [
                    int(area_id)
                    for area_id in raw_area_ids
                    if area_id.isdigit() and int(area_id) in valid_area_ids
                ]
                DatasetUserMappingArea.objects.filter(dataset=dataset, user_id=user_id).delete()
                if area_ids:
                    DatasetUserMappingArea.objects.bulk_create([
                        DatasetUserMappingArea(
                            dataset=dataset,
                            user_id=user_id,
                            mapping_area_id=area_id
                        ) for area_id in area_ids
                    ])
            
            if selected_group_set:
                DatasetGroupMappingArea.objects.filter(dataset=dataset).exclude(group_id__in=selected_group_set).delete()
            else:
                DatasetGroupMappingArea.objects.filter(dataset=dataset).delete()
            
            for group_id in selected_group_ids:
                raw_area_ids = request.POST.getlist(f'group_mapping_areas_{group_id}')
                area_ids = [
                    int(area_id)
                    for area_id in raw_area_ids
                    if area_id.isdigit() and int(area_id) in valid_area_ids
                ]
                DatasetGroupMappingArea.objects.filter(dataset=dataset, group_id=group_id).delete()
                if area_ids:
                    DatasetGroupMappingArea.objects.bulk_create([
                        DatasetGroupMappingArea(
                            dataset=dataset,
                            group_id=group_id,
                            mapping_area_id=area_id
                        ) for area_id in area_ids
                    ])
        else:
            DatasetUserMappingArea.objects.filter(dataset=dataset).delete()
            DatasetGroupMappingArea.objects.filter(dataset=dataset).delete()
        
        if not (users_to_add or users_to_remove or groups_to_add or groups_to_remove):
            messages.info(request, 'No changes were made to access settings.')
        
        return redirect('dataset_access', dataset_id=dataset.id)
    
    # Get all users and groups for selection
    all_users = list(User.objects.exclude(id=dataset.owner.id).order_by('username'))
    all_groups = list(Group.objects.order_by('name'))
    
    # Attach existing mapping area selections
    user_area_lookup = {}
    for relation in DatasetUserMappingArea.objects.filter(dataset=dataset):
        user_area_lookup.setdefault(relation.user_id, []).append(relation.mapping_area_id)
    
    group_area_lookup = {}
    for relation in DatasetGroupMappingArea.objects.filter(dataset=dataset):
        group_area_lookup.setdefault(relation.group_id, []).append(relation.mapping_area_id)
    
    for user in all_users:
        user.mapping_area_ids = user_area_lookup.get(user.id, [])
    
    for group in all_groups:
        group.mapping_area_ids = group_area_lookup.get(group.id, [])
    
    # Get currently shared users and groups
    shared_users = list(dataset.shared_with.values_list('id', flat=True))
    shared_groups = list(dataset.shared_with_groups.values_list('id', flat=True))
    
    return render(request, 'datasets/dataset_access.html', {
        'dataset': dataset,
        'all_users': all_users,
        'all_groups': all_groups,
        'shared_users': shared_users,
        'shared_groups': shared_groups,
        'mapping_areas': mapping_areas,
    })


@login_required
def dataset_data_input_view(request, dataset_id):
    """Data input view with map and entry editing"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)

    ensure_standard_dataset_fields(dataset)
    
    # Get all geometries for this dataset with their entries, respecting mapping area limits
    geometries_qs = DataGeometry.objects.filter(dataset=dataset).prefetch_related('entries')
    geometries = dataset.filter_geometries_for_user(geometries_qs, request.user)
    geometries = list(geometries)
    
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
    else:
        # Ensure custom fields are enabled if none are currently active
        standard_field_names = {field_def['field_name'] for field_def in STANDARD_DATASET_FIELDS}
        custom_enabled_fields = DatasetField.objects.filter(
            dataset=dataset,
            enabled=True
        ).exclude(field_name__in=standard_field_names)
        disabled_custom_fields = DatasetField.objects.filter(
            dataset=dataset,
            enabled=False
        ).exclude(field_name__in=standard_field_names)
        if not custom_enabled_fields.exists() and disabled_custom_fields.exists():
            disabled_custom_fields.update(enabled=True)
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
    
    # Get all users for allocation dropdown (only for dataset owner)
    users_for_allocation = []
    if dataset.owner == request.user:
        users_for_allocation = User.objects.filter(is_active=True).order_by('username')
    
    return render(request, 'datasets/dataset_data_input.html', {
        'dataset': dataset,
        'geometries': geometries,
        'typology_data': typology_data,
        'all_fields': all_fields,
        'fields_data': fields_data,
        'allow_multiple_entries': allow_multiple_entries,
        'users_for_allocation': users_for_allocation
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

    mapping_area_ids = dataset.get_user_mapping_area_ids(request.user)
    if mapping_area_ids is not None:
        restricted_geometries = dataset.filter_geometries_for_user(
            DataGeometry.objects.filter(dataset=dataset),
            request.user,
        )
        entries = entries.filter(geometry__in=restricted_geometries)
    
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

        ensure_standard_dataset_fields(dataset)
        
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
        else:
            standard_field_names = {field_def['field_name'] for field_def in STANDARD_DATASET_FIELDS}
            custom_enabled_fields = DatasetField.objects.filter(
                dataset=dataset,
                enabled=True
            ).exclude(field_name__in=standard_field_names)
            disabled_custom_fields = DatasetField.objects.filter(
                dataset=dataset,
                enabled=False
            ).exclude(field_name__in=standard_field_names)
            if not custom_enabled_fields.exists() and disabled_custom_fields.exists():
                disabled_custom_fields.update(enabled=True)
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
        
        geometries = dataset.filter_geometries_for_user(geometries, request.user)

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
        'field': field,
        'custom_field': field  # Backward compatibility for tests/templates expecting this key
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
