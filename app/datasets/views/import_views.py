from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.gis.geos import Point
import json
import csv
import io
import logging
from datetime import datetime
from django.db import connection, IntegrityError

from ..models import DataSet, DataGeometry, DataEntry, DataEntryField, DatasetField

# Set up logging for import debugging
logger = logging.getLogger(__name__)


def get_coordinate_system_name(srid):
    """Get coordinate system name from SRID"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT auth_name, auth_srid FROM spatial_ref_sys WHERE srid = %s", [srid])
            result = cursor.fetchone()
            if result:
                return f"{result[0]}:{result[1]}"
            return f"SRID:{srid}"
    except Exception:
        return f"SRID:{srid}"


def detect_csv_delimiter(csv_content, sample_size=1024):
    """Detect CSV delimiter from content with robust fallback scoring."""
    candidate_delimiters = [',', ';', '\t', '|']
    
    def _get_sample(content):
        if isinstance(content, bytes):
            return content[:sample_size].decode('utf-8', errors='ignore')
        return str(content)[:sample_size]
    
    sample = _get_sample(csv_content)
    
    # First try csv.Sniffer but only accept common delimiters
    try:
        sniffer = csv.Sniffer()
        sniffed = sniffer.sniff(sample)
        if sniffed.delimiter in candidate_delimiters:
            return sniffed.delimiter
    except Exception:
        pass
    
    # Custom scoring fallback
    lines = [line for line in sample.splitlines() if line.strip()]
    if not lines:
        return ','
    
    best_delimiter = ','
    best_score = float('-inf')
    
    for delimiter in candidate_delimiters:
        column_counts = []
        delimiter_occurrences = 0
        
        for line in lines:
            parts = line.split(delimiter)
            if len(parts) > 1:
                column_counts.append(len(parts))
                delimiter_occurrences += line.count(delimiter)
        
        if not column_counts:
            continue
        
        # Consistency metrics
        distinct_counts = set(column_counts)
        max_cols = max(column_counts)
        min_cols = min(column_counts)
        consistency_penalty = (max_cols - min_cols)
        
        # Score favors more rows with splits, higher occurrence and consistency
        score = (
            len(column_counts) * 10  # number of lines that split
            + delimiter_occurrences  # total delimiter occurrences
            + sum(column_counts)     # overall number of columns
            - consistency_penalty * 5  # penalize inconsistent column counts
            - len(distinct_counts) * 2
        )
        
        if score > best_score:
            best_score = score
            best_delimiter = delimiter
    
    if best_score == float('-inf'):
        return ','
    return best_delimiter


@login_required
def dataset_csv_column_selection_view(request, dataset_id):
    """CSV column selection view for import"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    # Get CSV data from session
    csv_data = request.session.get('csv_data')
    if not csv_data:
        messages.error(request, 'No CSV data found. Please upload a file first.')
        return redirect('dataset_csv_import', dataset_id=dataset.id)
    
    if request.method == 'POST':
        id_column = request.POST.get('id_column')
        coordinate_system = request.POST.get('coordinate_system')
        
        if id_column and coordinate_system:
            # Process the CSV import
            return process_csv_import(request, dataset, csv_data, 'imported_file.csv', id_column, coordinate_system)
        else:
            messages.error(request, 'Please select an ID column and coordinate system.')
    
    # Parse CSV to get column names
    try:
        delimiter = request.session.get('csv_delimiter', ',')
        logger.info(f"Using delimiter '{delimiter}' for column parsing")
        csv_reader = csv.DictReader(io.StringIO(csv_data), delimiter=delimiter)
        columns = csv_reader.fieldnames or []
        logger.info(f"Detected columns: {columns[:10]}...")  # Log first 10 columns
        
        # Check for potential ID conflicts
        id_conflicts = []
        if columns:
            # Get a sample of IDs from the CSV to check for conflicts
            csv_reader_sample = csv.DictReader(io.StringIO(csv_data), delimiter=delimiter)
            sample_ids = []
            for i, row in enumerate(csv_reader_sample):
                if i >= 10:  # Only check first 10 rows
                    break
                # Try common ID column names
                for id_col in ['id', 'ID', 'id_kurz', 'ID_KURZ', 'geometry_id', 'GEOMETRY_ID']:
                    if id_col in row and row[id_col].strip():
                        sample_ids.append(row[id_col].strip())
                        break
            
            if sample_ids:
                # Check if any of these IDs already exist in the current dataset
                existing_ids = DataGeometry.objects.filter(
                    dataset=dataset,
                    id_kurz__in=sample_ids
                ).values_list('id_kurz', flat=True)
                
                if existing_ids:
                    id_conflicts = list(existing_ids)
                    messages.warning(request, 
                        f'Warning: Some IDs in your CSV file already exist in this dataset: {", ".join(id_conflicts[:5])}'
                        + (f' (and {len(id_conflicts)-5} more)' if len(id_conflicts) > 5 else '') +
                        '. Consider using the "Clear existing data" option to replace existing data.'
                    )
        
    except Exception as e:
        logger.error(f"Error reading CSV: {str(e)}", exc_info=True)
        messages.error(request, f'Error reading CSV: {str(e)}')
        return redirect('dataset_csv_import', dataset_id=dataset.id)
    
    return render(request, 'datasets/dataset_csv_column_selection.html', {
        'dataset': dataset,
        'headers': columns,
        'id_conflicts': id_conflicts
    })


@login_required
def dataset_csv_import_view(request, dataset_id):
    """CSV import view"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if csv_file:
            try:
                # Read and decode the file
                decoded_file = csv_file.read().decode('utf-8')
                
                # Detect delimiter
                delimiter = detect_csv_delimiter(decoded_file)
                logger.info(f"Detected CSV delimiter: '{delimiter}' for file: {csv_file.name}")
                request.session['csv_delimiter'] = delimiter
                
                # Store CSV data in session
                request.session['csv_data'] = decoded_file
                
                # Redirect to column selection
                return redirect('dataset_csv_column_selection', dataset_id=dataset.id)
                
            except Exception as e:
                messages.error(request, f'Error reading CSV file: {str(e)}')
        else:
            messages.error(request, 'Please select a CSV file.')
    
    return render(request, 'datasets/dataset_csv_import.html', {
        'dataset': dataset
    })


@login_required
def process_csv_import(request, dataset, decoded_file, csv_file_name, id_column, coordinate_system):
    """Process CSV import and create geometries and entries"""
    try:
        # Clear existing data if requested
        if request.POST.get('clear_existing') == 'on':
            DataGeometry.objects.filter(dataset=dataset).delete()
            messages.info(request, 'Existing data cleared.')
        
        # Parse CSV
        delimiter = request.session.get('csv_delimiter', ',')
        csv_reader = csv.DictReader(io.StringIO(decoded_file), delimiter=delimiter)
        
        # Get coordinate columns
        x_column = request.POST.get('x_column', 'X')
        y_column = request.POST.get('y_column', 'Y')
        
        # Process coordinate system
        if coordinate_system == 'auto':
            # Try to detect coordinate system from data
            srid = 4326  # Default to WGS84
        else:
            srid = int(coordinate_system)
        
        imported_count = 0
        errors = []
        processed_ids = set()  # Track processed IDs within this dataset
        
        # First pass: collect all IDs and check for duplicates
        all_ids = []
        for row_num, row in enumerate(csv_reader, start=2):
            geometry_id = row.get(id_column, '').strip()
            if geometry_id:
                all_ids.append((row_num, geometry_id))
        
        # Check for duplicates within the CSV
        id_counts = {}
        for row_num, geometry_id in all_ids:
            if geometry_id in id_counts:
                errors.append(f'Row {row_num}: Duplicate ID "{geometry_id}" within CSV (first occurrence at row {id_counts[geometry_id]})')
            else:
                id_counts[geometry_id] = row_num
        
        # Check for existing geometries in the current dataset only
        existing_ids = set(DataGeometry.objects.filter(
            dataset=dataset,
            id_kurz__in=[id for _, id in all_ids]
        ).values_list('id_kurz', flat=True))
        
        # Filter out problematic IDs
        valid_ids = set()
        for row_num, geometry_id in all_ids:
            if geometry_id in existing_ids:
                errors.append(f'Row {row_num}: ID "{geometry_id}" already exists in this dataset')
            else:
                valid_ids.add(geometry_id)
        
        
        # Reset CSV reader for second pass
        csv_reader = csv.DictReader(io.StringIO(decoded_file), delimiter=delimiter)
        
        with transaction.atomic():
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 for header
                try:
                    # Get ID and coordinates
                    geometry_id = row.get(id_column, '').strip()
                    x_coord = row.get(x_column, '').strip()
                    y_coord = row.get(y_column, '').strip()
                    
                    if not geometry_id or not x_coord or not y_coord:
                        errors.append(f'Row {row_num}: Missing required data')
                        continue
                    
                    # Skip if ID is not valid
                    if geometry_id not in valid_ids:
                        continue
                    
                    # Convert coordinates
                    try:
                        x = float(x_coord)
                        y = float(y_coord)
                    except ValueError:
                        errors.append(f'Row {row_num}: Invalid coordinates')
                        continue
                    
                    # Create geometry point
                    geometry = DataGeometry.objects.create(
                        dataset=dataset,
                        id_kurz=geometry_id,
                        address=f'Unknown Address ({geometry_id})',
                        geometry=Point(x, y, srid=srid),
                        user=request.user
                    )
                    
                    # Create entry
                    entry = DataEntry.objects.create(
                        geometry=geometry,
                        name=geometry_id,
                        user=request.user
                    )
                    
                    # Create field values for all other columns
                    for column, value in row.items():
                        if column not in [id_column, x_column, y_column] and value.strip():
                            # Create dataset field if it doesn't exist
                            field, created = DatasetField.objects.get_or_create(
                                dataset=dataset,
                                field_name=column,
                                defaults={
                                    'label': column,
                                    'field_type': 'text',
                                    'enabled': True
                                }
                            )
                            
                            # Create entry field
                            DataEntryField.objects.create(
                                entry=entry,
                                field_name=column,
                                value=value.strip()
                            )
                    
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f'Row {row_num}: {str(e)}')
                    logger.error(f"Error importing row {row_num}: {str(e)}", exc_info=True)
        
        # Clear session data
        if 'csv_data' in request.session:
            del request.session['csv_data']
        if 'csv_delimiter' in request.session:
            del request.session['csv_delimiter']
        
        if errors:
            messages.warning(request, f'Imported {imported_count} geometries with {len(errors)} errors.')
            for error in errors[:10]:  # Show first 10 errors
                messages.error(request, error)
        else:
            messages.success(request, f'Successfully imported {imported_count} geometries.')
        
        return redirect('dataset_detail', dataset_id=dataset.id)
        
    except Exception as e:
        logger.error(f"Critical error during CSV import: {str(e)}", exc_info=True)
        messages.error(request, f'Error processing CSV file: {str(e)}')
        return render(request, 'datasets/dataset_csv_import.html', {'dataset': dataset})


@login_required
def import_summary_view(request, dataset_id):
    """Display import summary for a dataset"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    # Calculate current dataset statistics
    total_geometries = DataGeometry.objects.filter(dataset=dataset).count()
    total_entries = DataEntry.objects.filter(geometry__dataset=dataset).count()
    
    return render(request, 'datasets/import_summary.html', {
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
        return render(request, 'datasets/403.html', status=403)
    
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    if request.method == 'POST':
        # Create a sample CSV for testing
        sample_csv = """ID,ADRESSE,GEB_X,GEB_Y,2016_NUTZUNG,2016_CAT_INNO,2016_CAT_WERT,2016_CAT_FILI,2022_NUTZUNG,2022_CAT_INNO,2022_CAT_WERT,2022_CAT_FILI
test_001,Test Address 1,656610,3399131,870,999,999,999,870,999,999,999
test_002,Test Address 2,656620,3399141,640,0,0,0,640,0,0,0"""
        
        # Process the sample CSV
        return process_csv_import(request, dataset, sample_csv, 'sample.csv', 'ID', 'auto')
    
    return render(request, 'datasets/debug_import.html', {
        'dataset': dataset
    })


@login_required
def dataset_export_options_view(request, dataset_id):
    """Export options for a dataset"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    # Get counts for geometries and data entries
    geometries_count = DataGeometry.objects.filter(dataset=dataset).count()
    data_entries_count = DataEntry.objects.filter(geometry__dataset=dataset).count()
    
    # Get unique years from entries
    years = DataEntry.objects.filter(geometry__dataset=dataset).values_list('year', flat=True).distinct().order_by('year')
    years = [str(year) for year in years if year is not None]
    
    # Get enabled fields for this dataset
    enabled_fields = DatasetField.objects.filter(dataset=dataset, enabled=True).order_by('order', 'field_name')
    
    # Get field statistics
    field_stats = {}
    for field in enabled_fields:
        # Count how many entries have values for this field
        field_usage_count = DataEntryField.objects.filter(
            entry__geometry__dataset=dataset,
            field_name=field.field_name
        ).count()
        
        field_stats[field.field_name] = {
            'label': field.label,
            'field_type': field.get_field_type_display(),
            'usage_count': field_usage_count,
            'is_coordinate': field.is_coordinate_field,
            'is_id': field.is_id_field,
            'is_address': field.is_address_field
        }
    
    # Get coordinate system information
    coordinate_systems = set()
    for geometry in DataGeometry.objects.filter(dataset=dataset):
        coordinate_systems.add(geometry.geometry.srid)
    
    return render(request, 'datasets/dataset_export.html', {
        'dataset': dataset,
        'geometries_count': geometries_count,
        'data_entries_count': data_entries_count,
        'years': years,
        'enabled_fields': enabled_fields,
        'field_stats': field_stats,
        'coordinate_systems': list(coordinate_systems)
    })


@login_required
def dataset_csv_export_view(request, dataset_id):
    """Export dataset as CSV"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    # Get export options
    include_coordinates = request.GET.get('include_coordinates', 'true').lower() == 'true'
    include_empty_years = request.GET.get('include_empty_years', 'true').lower() == 'true'
    
    # Get all geometries and their entries
    geometries = DataGeometry.objects.filter(dataset=dataset).prefetch_related('entries__fields')
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{dataset.name}_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Build header based on options
    header = ['ID', 'Address']
    
    if include_coordinates:
        header.extend(['X', 'Y'])
    
    header.extend(['User', 'Entry_Name', 'Year'])
    
    # Get all unique field names from enabled fields
    enabled_field_names = set(DatasetField.objects.filter(
        dataset=dataset, 
        enabled=True
    ).values_list('field_name', flat=True))
    
    # Also get field names from actual data
    data_field_names = set()
    for geometry in geometries:
        for entry in geometry.entries.all():
            for field in entry.fields.all():
                data_field_names.add(field.field_name)
    
    # Combine field names (prioritize enabled fields)
    all_field_names = enabled_field_names.union(data_field_names)
    
    # Add field names to header
    header.extend(sorted(all_field_names))
    writer.writerow(header)
    
    # Write data
    for geometry in geometries:
        for entry in geometry.entries.all():
            row = [
                geometry.id_kurz,
                geometry.address
            ]
            
            if include_coordinates:
                row.extend([
                    geometry.geometry.x,
                    geometry.geometry.y
                ])
            
            row.extend([
                geometry.user.username if geometry.user else 'Unknown',
                entry.name or '',
                entry.year or ''
            ])
            
            # Add field values
            field_values = {field.field_name: field.value for field in entry.fields.all()}
            for field_name in sorted(all_field_names):
                row.append(field_values.get(field_name, ''))
            
            writer.writerow(row)
    
    return response
