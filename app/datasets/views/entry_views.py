from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction

from ..models import DataSet, DataGeometry, DataEntry, DataEntryField, DatasetField


@login_required
def entry_detail_view(request, entry_id):
    """View details of a specific entry"""
    entry = get_object_or_404(DataEntry, id=entry_id)
    dataset = entry.geometry.dataset
    
    # Check if user has access to this entry's dataset
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    # Get all fields for this dataset, ordered by display order
    all_fields = DatasetField.objects.filter(dataset=dataset).order_by('order', 'field_name')
    
    return render(request, 'datasets/entry_detail.html', {
        'entry': entry,
        'dataset': dataset,
        'all_fields': all_fields
    })


@login_required
def entry_edit_view(request, entry_id):
    """Edit an existing entry"""
    entry = get_object_or_404(DataEntry, id=entry_id)
    
    # Check if user has access to this entry's dataset
    if not entry.geometry.dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        year = request.POST.get('year')
        
        if name:
            entry.name = name
            if year:
                try:
                    entry.year = int(year)
                except ValueError:
                    pass
            entry.save()
            
            # Update field values
            for field in entry.fields.all():
                field_name = field.field_name
                if field_name in request.POST:
                    field.value = request.POST[field_name]
                    field.save()
            
            messages.success(request, 'Entry updated successfully!')
            return redirect('entry_detail', entry_id=entry.id)
        else:
            messages.error(request, 'Entry name is required.')
    
    # Get all fields for this dataset, ordered by display order
    dataset = entry.geometry.dataset
    all_fields = DatasetField.objects.filter(dataset=dataset).order_by('order', 'field_name')
    
    return render(request, 'datasets/entry_edit.html', {
        'entry': entry,
        'dataset': dataset,
        'all_fields': all_fields
    })


@login_required
def entry_create_view(request, geometry_id):
    """Create a new entry for a geometry"""
    geometry = get_object_or_404(DataGeometry, id=geometry_id)
    
    # Check if user has access to this geometry's dataset
    if not geometry.dataset.can_access(request.user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        year = request.POST.get('year')
        
        if name:
            try:
                year_int = int(year) if year else None
            except ValueError:
                year_int = None
            
            # Create entry
            entry = DataEntry.objects.create(
                geometry=geometry,
                name=name,
                year=year_int,
                user=request.user
            )
            
            # Create field values
            for key, value in request.POST.items():
                if key not in ['name', 'year', 'geometry_id', 'csrfmiddlewaretoken']:
                    # Skip empty values to avoid creating empty fields
                    if value and value.strip():
                        DataEntryField.objects.create(
                            entry=entry,
                            field_name=key,
                            value=value.strip()
                        )
            
            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Entry "{name}" created successfully!',
                    'entry_id': entry.id
                })
            
            messages.success(request, f'Entry "{name}" created successfully!')
            return redirect('dataset_data_input', dataset_id=geometry.dataset.id)
        else:
            error_msg = 'Entry name is required.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            messages.error(request, error_msg)
    
    return render(request, 'datasets/entry_create.html', {
        'geometry': geometry
    })


@login_required
def save_entries_view(request):
    """Save entries with updated field values"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'}, status=405)
    
    try:
        geometry_id = request.POST.get('geometry_id')
        if not geometry_id:
            return JsonResponse({'success': False, 'error': 'Geometry ID is required'}, status=400)
        
        # Get the geometry
        try:
            geometry = DataGeometry.objects.get(pk=geometry_id)
        except DataGeometry.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Geometry not found'}, status=404)
        
        # Check if user has access to this dataset
        if not geometry.dataset.can_access(request.user):
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        # Process entries data
        entries_data = {}
        for key, value in request.POST.items():
            if key.startswith('entries[') and key.endswith(']'):
                # Parse key like "entries[0][id]" or "entries[0][fields][field_name]"
                parts = key.split('[')
                if len(parts) >= 2:
                    entry_index = parts[1].rstrip(']')
                    if entry_index not in entries_data:
                        entries_data[entry_index] = {'id': None, 'fields': {}}
                    
                    if len(parts) == 3:  # entries[0][id]
                        entries_data[entry_index]['id'] = value
                    elif len(parts) == 4:  # entries[0][fields][field_name]
                        field_name = parts[3].rstrip(']')
                        entries_data[entry_index]['fields'][field_name] = value
        
        # Update entries
        updated_count = 0
        for entry_data in entries_data.values():
            if entry_data['id']:
                try:
                    entry = DataEntry.objects.get(pk=entry_data['id'])
                    
                    # Update field values
                    for field_name, field_value in entry_data['fields'].items():
                        # Get or create DataEntryField
                        field_obj, created = DataEntryField.objects.get_or_create(
                            entry=entry,
                            field_name=field_name,
                            defaults={'value': field_value}
                        )
                        if not created:
                            field_obj.value = field_value
                            field_obj.save()
                    
                    updated_count += 1
                except DataEntry.DoesNotExist:
                    continue
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully updated {updated_count} entries'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
