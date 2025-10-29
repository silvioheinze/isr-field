from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
import csv
import json
import io

from ..models import DataSet, Typology, TypologyEntry
from .auth_views import is_manager


@login_required
def typology_create_view(request):
    """Create a new typology"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        if name:
            typology = Typology.objects.create(
                name=name,
                description=description
            )
            messages.success(request, f'Typology "{name}" created successfully!')
            return redirect('typology_detail', typology_id=typology.id)
        else:
            messages.error(request, 'Typology name is required.')
    
    return render(request, 'datasets/typology_create.html')


@login_required
def typology_edit_view(request, typology_id):
    """Edit a typology"""
    typology = get_object_or_404(Typology, id=typology_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        
        if name:
            typology.name = name
            typology.description = description
            typology.save()
            
            messages.success(request, 'Typology updated successfully!')
            return redirect('typology_detail', typology_id=typology.id)
        else:
            messages.error(request, 'Typology name is required.')
    
    return render(request, 'datasets/typology_edit.html', {
        'typology': typology
    })


@login_required
def typology_list_view(request):
    """List all typologies"""
    typologies = Typology.objects.all()
    return render(request, 'datasets/typology_list.html', {
        'typologies': typologies,
        'can_create_typologies': is_manager(request.user)
    })


@login_required
def typology_detail_view(request, typology_id):
    """View typology details"""
    typology = get_object_or_404(Typology, id=typology_id)
    entries = TypologyEntry.objects.filter(typology=typology).order_by('code')
    
    return render(request, 'datasets/typology_detail.html', {
        'typology': typology,
        'entries': entries
    })


@login_required
def typology_import_view(request, typology_id):
    """Import typology entries from CSV"""
    typology = get_object_or_404(Typology, id=typology_id)
    
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if csv_file:
            try:
                # Read and decode the file
                decoded_file = csv_file.read().decode('utf-8')
                
                # Parse CSV
                csv_reader = csv.DictReader(io.StringIO(decoded_file))
                
                imported_count = 0
                for row in csv_reader:
                    code = row.get('code')
                    category = row.get('category')
                    name = row.get('name')
                    
                    if code and category and name:
                        TypologyEntry.objects.create(
                            typology=typology,
                            code=int(code),
                            category=category,
                            name=name
                        )
                        imported_count += 1
                
                messages.success(request, f'Successfully imported {imported_count} typology entries!')
                return redirect('typology_detail', typology_id=typology.id)
                
            except Exception as e:
                messages.error(request, f'Error importing CSV: {str(e)}')
        else:
            messages.error(request, 'Please select a CSV file.')
    
    return render(request, 'datasets/typology_import.html', {
        'typology': typology
    })


@login_required
def typology_export_view(request, typology_id):
    """Export typology as CSV"""
    typology = get_object_or_404(Typology, id=typology_id)
    entries = TypologyEntry.objects.filter(typology=typology).order_by('code')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{typology.name}_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Code', 'Category', 'Name'])
    
    for entry in entries:
        writer.writerow([entry.code, entry.category, entry.name])
    
    return response
