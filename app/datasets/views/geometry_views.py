from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.gis.geos import Point

from ..models import DataSet, DataGeometry, DataEntry, DataEntryField, DatasetField


@login_required
def geometry_create_view(request, dataset_id):
    """Create a new geometry point"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        id_kurz = request.POST.get('id_kurz')
        address = request.POST.get('address')
        lng = request.POST.get('lng')
        lat = request.POST.get('lat')
        
        if id_kurz and lng and lat:
            try:
                # Create geometry point
                geometry = DataGeometry.objects.create(
                    dataset=dataset,
                    id_kurz=id_kurz,
                    address=address or f'Unknown Address ({id_kurz})',
                    geometry=Point(float(lng), float(lat)),
                    user=request.user
                )
                
                messages.success(request, f'Geometry point "{id_kurz}" created successfully!')
                return redirect('dataset_data_input', dataset_id=dataset.id)
            except Exception as e:
                messages.error(request, f'Error creating geometry: {str(e)}')
        else:
            messages.error(request, 'ID, longitude, and latitude are required.')
    
    return render(request, 'datasets/geometry_create.html', {
        'dataset': dataset
    })


@login_required
def geometry_details_view(request, geometry_id):
    """API endpoint to get detailed data for a specific geometry point"""
    try:
        geometry = get_object_or_404(DataGeometry, pk=geometry_id)
        if not geometry.dataset.can_access(request.user):
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        # Get enabled fields for this dataset in the correct order
        enabled_fields = DatasetField.objects.filter(
            dataset=geometry.dataset, 
            enabled=True
        ).order_by('order', 'field_name')
        
        # Prepare detailed geometry data
        geometry_data = {
            'id': geometry.id,
            'id_kurz': geometry.id_kurz,
            'address': geometry.address,
            'lat': geometry.geometry.y,
            'lng': geometry.geometry.x,
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
            
            # Add only enabled field values in the correct order
            for field_config in enabled_fields:
                # Find the corresponding field value for this entry
                field_value = entry.fields.filter(field_name=field_config.field_name).first()
                if field_value:
                    entry_data[field_config.field_name] = field_value.get_typed_value()
                else:
                    # Field is configured but no data exists yet
                    entry_data[field_config.field_name] = None
            
            geometry_data['entries'].append(entry_data)
        
        return JsonResponse({
            'success': True,
            'geometry': geometry_data
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
