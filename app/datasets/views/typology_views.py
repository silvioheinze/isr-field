from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
import csv
import json
import io
import re

from ..models import Typology, TypologyEntry, DatasetField
from .auth_views import is_manager


@login_required
def typology_create_view(request):
    """Create a new typology"""
    dataset_id = request.GET.get('dataset_id') or request.POST.get('dataset_id')
    name_value = (request.POST.get('name') or '').strip() if request.method == 'POST' else ''
    initial_entries = []
    name_errors = []

    if request.method == 'POST':
        suffix_pattern = re.compile(r'^entry_code_(?P<suffix>.+)$')
        suffixes = []
        for key in request.POST.keys():
            match = suffix_pattern.match(key)
            if match:
                suffixes.append(match.group('suffix'))
        suffixes = sorted(set(suffixes), key=lambda s: int(s) if s.isdigit() else s)

        entries_raw = []
        for suffix in suffixes:
            code_raw = (request.POST.get(f'entry_code_{suffix}') or '').strip()
            category_raw = (request.POST.get(f'entry_category_{suffix}') or '').strip()
            name_raw = (request.POST.get(f'entry_name_{suffix}') or '').strip()
            if not code_raw and not category_raw and not name_raw:
                continue
            entries_raw.append({
                'code': code_raw,
                'category': category_raw,
                'name': name_raw,
            })

        errors = []
        if not name_value:
            error_msg = 'Typology name is required.'
            name_errors.append(error_msg)
            errors.append(error_msg)

        if not entries_raw:
            errors.append('Please add at least one typology entry.')

        normalized_entries = []
        seen_codes = set()
        for index, entry in enumerate(entries_raw, start=1):
            code_raw = entry['code']
            category = entry['category']
            entry_name = entry['name']

            if not code_raw:
                errors.append(f'Entry #{index}: Code is required.')
                continue
            try:
                code_int = int(code_raw)
            except ValueError:
                errors.append(f'Entry #{index}: Code "{code_raw}" must be a number.')
                continue

            if code_int in seen_codes:
                errors.append(f'Entry #{index}: Duplicate code {code_int} detected.')
                continue
            seen_codes.add(code_int)

            if not category:
                errors.append(f'Entry #{index}: Category is required.')
            if not entry_name:
                errors.append(f'Entry #{index}: Name is required.')

            normalized_entries.append({
                'code': code_int,
                'category': category,
                'name': entry_name,
            })

        if not errors:
            try:
                with transaction.atomic():
                    typology = Typology.objects.create(
                        name=name_value,
                        created_by=request.user
                    )
                    TypologyEntry.objects.bulk_create([
                        TypologyEntry(
                            typology=typology,
                            code=entry['code'],
                            category=entry['category'],
                            name=entry['name']
                        )
                        for entry in normalized_entries
                    ])
                messages.success(request, f'Typology "{name_value}" created with {len(normalized_entries)} entries.')
                return redirect('typology_detail', typology_id=typology.id)
            except Exception as exc:
                errors.append(f'Error creating typology: {exc}')

        for message_text in errors:
            messages.error(request, message_text)

        initial_entries = entries_raw

    context = {
        'name_value': name_value,
        'name_errors': name_errors,
        'initial_entries': initial_entries,
    }
    if dataset_id:
        context['dataset_id'] = dataset_id

    return render(request, 'datasets/typology_create.html', context)


@login_required
def typology_edit_view(request, typology_id):
    """Edit a typology"""
    typology = get_object_or_404(Typology, id=typology_id)
    
    # Only typology creator can edit
    if typology.created_by != request.user:
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        
        if name:
            typology.name = name
            typology.save()
            
            messages.success(request, 'Typology updated successfully!')
            return redirect('typology_detail', typology_id=typology.id)
        else:
            messages.error(request, 'Typology name is required.')
    
    return render(request, 'datasets/typology_edit.html', {
        'typology': typology,
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
    linked_fields_qs = DatasetField.objects.filter(typology=typology).select_related('dataset').order_by('dataset__name', 'order', 'label')

    linked_fields = list(linked_fields_qs)
    fields_by_dataset = []
    for field in linked_fields:
        dataset = field.dataset
        if fields_by_dataset and fields_by_dataset[-1]['dataset'].id == dataset.id:
            fields_by_dataset[-1]['fields'].append(field)
        else:
            fields_by_dataset.append({
                'dataset': dataset,
                'fields': [field],
            })

    linked_dataset_count = len(fields_by_dataset)
    linked_field_count = len(linked_fields)

    return render(request, 'datasets/typology_detail.html', {
        'typology': typology,
        'entries': entries,
        'fields_by_dataset': fields_by_dataset,
        'linked_dataset_count': linked_dataset_count,
        'linked_field_count': linked_field_count,
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
                
                # Detect delimiter using csv.Sniffer
                try:
                    import csv
                    sample = decoded_file[:1024]  # Use first 1KB for detection
                    sniffer = csv.Sniffer()
                    delimiter = sniffer.sniff(sample).delimiter
                except Exception as e:
                    # Fallback to manual detection
                    delimiter = ','
                    if ';' in decoded_file[:100]:
                        delimiter = ';'
                    elif '\t' in decoded_file[:100]:
                        delimiter = '\t'
                
                # Parse CSV
                csv_reader = csv.DictReader(io.StringIO(decoded_file), delimiter=delimiter)
                
                # Check if required columns exist (case-insensitive)
                fieldnames_lower = []
                if csv_reader.fieldnames:
                    for raw_name in csv_reader.fieldnames:
                        if raw_name is None:
                            continue
                        normalized_name = str(raw_name).strip().lower()
                        if normalized_name:
                            fieldnames_lower.append(normalized_name)
                required_columns = ['code', 'category', 'name']
                missing_columns = [col for col in required_columns if col not in fieldnames_lower]
                
                if missing_columns:
                    found_columns_list = [str(name) if name is not None else '(blank)' for name in (csv_reader.fieldnames or [])]
                    found_columns = ', '.join(found_columns_list) if found_columns_list else 'none'
                    error_msg = f"Missing required columns: {', '.join(missing_columns)}. Found columns: {found_columns}"
                    messages.error(request, error_msg)
                    return redirect('typology_import', typology_id=typology.id)
                
                imported_count = 0
                row_count = 0
                errors = []
                
                for row in csv_reader:
                    row_count += 1
                    
                    # Case-insensitive column access with safe key handling
                    code = category = name = None
                    for key, value in row.items():
                        if key is None:
                            continue
                        key_lower = str(key).strip().lower()
                        if key_lower == 'code':
                            code = value
                        elif key_lower == 'category':
                            category = value
                        elif key_lower == 'name':
                            name = value
                    
                    if code and category and name:
                        try:
                            # Clean the values
                            code = str(code).strip()
                            category = str(category).strip()
                            name = str(name).strip()
                            
                            if code and category and name:
                                TypologyEntry.objects.create(
                                    typology=typology,
                                    code=int(code),
                                    category=category,
                                    name=name
                                )
                                imported_count += 1
                        except ValueError as e:
                            error_msg = f"Row {row_count}: Invalid code '{code}' - must be a number"
                            errors.append(error_msg)
                        except Exception as e:
                            error_msg = f"Row {row_count}: Error creating entry: {str(e)}"
                            errors.append(error_msg)
                    else:
                        errors.append(f"Row {row_count}: Missing required values (code, category, or name)")
                
                if errors:
                    error_summary = f"Imported {imported_count} entries with {len(errors)} errors: " + "; ".join(errors[:3])
                    if len(errors) > 3:
                        error_summary += f" (and {len(errors) - 3} more errors)"
                    messages.warning(request, error_summary)
                else:
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


@login_required
def typology_delete_view(request, typology_id):
    """Delete an existing typology."""
    typology = get_object_or_404(Typology, id=typology_id)

    if typology.created_by != request.user:
        return render(request, 'datasets/403.html', status=403)

    if request.method == 'POST':
        typology_name = typology.name
        typology.delete()
        messages.success(request, f'Typology "{typology_name}" deleted successfully.')
        return redirect('typology_list')

    return render(request, 'datasets/typology_delete.html', {
        'typology': typology,
    })
