"""
Background tasks for file export operations.

This module handles asynchronous ZIP file generation and email notifications.
"""

import os
import zipfile
import uuid
import json
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.db import transaction
from django.core.files.storage import default_storage
from django.contrib.auth.models import User

from .models import DataSet, DataEntryFile, ExportTask


def generate_zip_export(task_id, dataset_id, user_id, file_types=None, date_from=None, date_to=None, 
                       organize_by='geometry', include_metadata=True):
    """
    Generate ZIP export asynchronously.
    
    Args:
        task_id: Unique task identifier
        dataset_id: ID of the dataset to export
        user_id: ID of the user requesting the export
        file_types: List of file types to include
        date_from: Start date for filtering
        date_to: End date for filtering
        organize_by: How to organize files
        include_metadata: Whether to include metadata files
    """
    try:
        # Get objects
        dataset = DataSet.objects.get(id=dataset_id)
        user = User.objects.get(id=user_id)
        
        # Update task status
        with transaction.atomic():
            task = ExportTask.objects.get(task_id=task_id)
            task.status = 'processing'
            task.save()
        
        # Get filtered files
        files_queryset = get_filtered_files(dataset, file_types, date_from, date_to)
        
        if not files_queryset.exists():
            raise ValueError("No files found matching the specified criteria")
        
        # Create export directory
        export_dir = Path(settings.MEDIA_ROOT) / 'exports' / task_id
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate ZIP file
        zip_filename = f"{dataset.name}_files_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = export_dir / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add files to ZIP with geometry/entry ID prefixes
            for file_obj in files_queryset:
                if file_obj.file and default_storage.exists(file_obj.file.name):
                    # Create filename with geometry/entry ID prefix
                    prefixed_filename = create_prefixed_filename(file_obj, organize_by)
                    
                    # Read file content
                    try:
                        with default_storage.open(file_obj.file.name, 'rb') as f:
                            zipf.writestr(prefixed_filename, f.read())
                    except Exception as e:
                        print(f"Error reading file {file_obj.filename}: {e}")
                        continue
                else:
                    print(f"File not found: {file_obj.filename}")
            
            # Add metadata if requested
            if include_metadata:
                add_metadata_to_zip(zipf, files_queryset, dataset, organize_by)
        
        # Update task with completion
        file_size = zip_path.stat().st_size
        with transaction.atomic():
            task = ExportTask.objects.get(task_id=task_id)
            task.status = 'completed'
            task.file_path = str(zip_path.relative_to(settings.MEDIA_ROOT))
            task.file_size = file_size
            task.completed_at = datetime.now()
            task.save()
        
        # Send email notification
        send_export_completion_email(user, dataset, task, zip_path)
        
        print(f"ZIP export completed: {zip_path}")
        
    except Exception as e:
        # Update task with error
        with transaction.atomic():
            task = ExportTask.objects.get(task_id=task_id)
            task.status = 'failed'
            task.error_message = str(e)
            task.completed_at = datetime.now()
            task.save()
        
        print(f"ZIP export failed: {e}")
        raise


def get_filtered_files(dataset, file_types=None, date_from=None, date_to=None):
    """Get filtered files based on criteria."""
    files_queryset = DataEntryFile.objects.filter(
        entry__geometry__dataset=dataset
    ).select_related('entry', 'entry__geometry', 'upload_user')
    
    # File type filter
    if file_types and 'all' not in file_types:
        if 'image' in file_types:
            files_queryset = files_queryset.filter(file_type__startswith='image/')
        if 'document' in file_types:
            files_queryset = files_queryset.exclude(file_type__startswith='image/')
    
    # Date filters
    if date_from:
        files_queryset = files_queryset.filter(upload_date__date__gte=date_from)
    if date_to:
        files_queryset = files_queryset.filter(upload_date__date__lte=date_to)
    
    return files_queryset.order_by('entry__geometry__id_kurz', 'upload_date')


def create_prefixed_filename(file_obj, organize_by):
    """Create filename with geometry/entry ID prefix."""
    geometry_id = file_obj.entry.geometry.id_kurz
    entry_id = file_obj.entry.id
    original_filename = file_obj.filename
    
    # Get file extension
    if '.' in original_filename:
        name, ext = original_filename.rsplit('.', 1)
        ext = f'.{ext}'
    else:
        name = original_filename
        ext = ''
    
    if organize_by == 'geometry':
        # Format: geometry_A1_photo1.jpg
        prefixed_name = f"geometry_{geometry_id}_{name}{ext}"
    elif organize_by == 'entry':
        # Format: entry_123_photo1.jpg
        prefixed_name = f"entry_{entry_id}_{name}{ext}"
    elif organize_by == 'date':
        # Format: 2024-01-15_geometry_A1_photo1.jpg
        date_str = file_obj.upload_date.strftime('%Y-%m-%d')
        prefixed_name = f"{date_str}_geometry_{geometry_id}_{name}{ext}"
    elif organize_by == 'user':
        # Format: user_john_geometry_A1_photo1.jpg
        user_str = file_obj.upload_user.username if file_obj.upload_user else 'unknown'
        prefixed_name = f"user_{user_str}_geometry_{geometry_id}_{name}{ext}"
    elif organize_by == 'type':
        # Format: image_geometry_A1_photo1.jpg
        file_type = file_obj.file_type.split('/')[0]
        prefixed_name = f"{file_type}_geometry_{geometry_id}_{name}{ext}"
    else:
        # Default: geometry_A1_photo1.jpg
        prefixed_name = f"geometry_{geometry_id}_{name}{ext}"
    
    return prefixed_name


def add_metadata_to_zip(zipf, files_queryset, dataset, organize_by):
    """Add metadata files to ZIP archive."""
    # Create file manifest
    manifest_data = []
    for file_obj in files_queryset:
        prefixed_filename = create_prefixed_filename(file_obj, organize_by)
        manifest_data.append({
            'file_id': file_obj.id,
            'original_filename': file_obj.filename,
            'prefixed_filename': prefixed_filename,
            'file_type': file_obj.file_type,
            'file_size': file_obj.file_size,
            'upload_date': file_obj.upload_date.isoformat(),
            'upload_user': file_obj.upload_user.username if file_obj.upload_user else 'Unknown',
            'geometry_id': file_obj.entry.geometry.id_kurz,
            'entry_id': file_obj.entry.id,
            'entry_name': file_obj.entry.name,
            'geometry_address': file_obj.entry.geometry.address,
            'description': file_obj.description or '',
        })
    
    # Add JSON manifest
    zipf.writestr('files_manifest.json', json.dumps(manifest_data, indent=2))
    
    # Add CSV manifest
    csv_buffer = []
    if manifest_data:
        fieldnames = manifest_data[0].keys()
        csv_buffer.append(','.join(fieldnames))
        for row in manifest_data:
            csv_buffer.append(','.join(f'"{str(v)}"' for v in row.values()))
    
    zipf.writestr('files_manifest.csv', '\n'.join(csv_buffer))
    
    # Add dataset summary
    stats = calculate_file_statistics(files_queryset)
    summary = {
        'dataset_name': dataset.name,
        'dataset_id': dataset.id,
        'export_date': datetime.now().isoformat(),
        'total_files': stats['total_files'],
        'total_size_bytes': stats['total_size'],
        'total_size_mb': round(stats['total_size'] / (1024 * 1024), 2),
        'file_types': stats['file_types'],
        'users': stats['users'],
        'geometries': stats['geometries'],
        'date_range': stats['date_range'],
        'organization_method': organize_by
    }
    zipf.writestr('dataset_summary.json', json.dumps(summary, indent=2))
    
    # Add README
    readme_content = f"""# Dataset Files Export: {dataset.name}

## Export Information
- **Export Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Total Files**: {stats['total_files']}
- **Total Size**: {round(stats['total_size'] / (1024 * 1024), 2)} MB
- **Organization Method**: {organize_by}
- **Date Range**: {stats['date_range']['earliest']} to {stats['date_range']['latest']}

## File Naming Convention
Files are prefixed with geometry/entry identifiers for easy identification:
- **Geometry ID**: {dataset.geometries.first().id_kurz if dataset.geometries.exists() else 'N/A'}
- **Entry ID**: Sequential entry numbers
- **Format**: geometry_{{ID}}_{{original_filename}} or entry_{{ID}}_{{original_filename}}

## File Types
{chr(10).join([f"- {ftype}: {count} files" for ftype, count in stats['file_types'].items()])}

## Contributing Users
{chr(10).join([f"- {user}: {count} files" for user, count in stats['users'].items()])}

## Metadata Files
- `files_manifest.json`: Detailed file information in JSON format
- `files_manifest.csv`: Detailed file information in CSV format
- `dataset_summary.json`: Complete dataset and export statistics

## Usage Notes
- All file paths are relative to this ZIP archive
- Original file names and metadata are preserved
- Use the manifest files for programmatic access to file information
- Files are organized with clear naming conventions for easy identification
"""
    
    zipf.writestr('README.md', readme_content)


def calculate_file_statistics(files_queryset):
    """Calculate comprehensive file statistics."""
    stats = {
        'total_files': files_queryset.count(),
        'total_size': sum(f.file_size for f in files_queryset if f.file_size),
        'file_types': {},
        'users': {},
        'geometries': {},
        'date_range': {'earliest': None, 'latest': None},
    }
    
    for file_obj in files_queryset:
        # File type stats
        file_type = file_obj.file_type.split('/')[0]
        stats['file_types'][file_type] = stats['file_types'].get(file_type, 0) + 1
        
        # User stats
        user = file_obj.upload_user.username if file_obj.upload_user else 'Unknown'
        stats['users'][user] = stats['users'].get(user, 0) + 1
        
        # Geometry stats
        geom_id = file_obj.entry.geometry.id_kurz
        stats['geometries'][geom_id] = stats['geometries'].get(geom_id, 0) + 1
        
        # Date range
        upload_date = file_obj.upload_date.date()
        if not stats['date_range']['earliest'] or upload_date < stats['date_range']['earliest']:
            stats['date_range']['earliest'] = upload_date
        if not stats['date_range']['latest'] or upload_date > stats['date_range']['latest']:
            stats['date_range']['latest'] = upload_date
    
    return stats


def send_export_completion_email(user, dataset, task, zip_path):
    """Send email notification when export is completed."""
    try:
        # Create download URL
        download_url = f"{settings.MEDIA_URL}{task.file_path}"
        
        # Prepare email context
        context = {
            'user': user,
            'dataset': dataset,
            'task': task,
            'download_url': download_url,
            'file_size_mb': round(task.file_size / (1024 * 1024), 2) if task.file_size else 0,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        }
        
        # Render email content
        subject = f"{settings.EMAIL_SUBJECT_PREFIX}File Export Completed - {dataset.name}"
        
        # Create HTML email content
        html_message = render_to_string('datasets/emails/export_completion.html', context)
        
        # Create plain text email content
        text_message = f"""
Hello {user.get_full_name() or user.username},

Your file export for dataset "{dataset.name}" has been completed successfully!

Export Details:
- Dataset: {dataset.name}
- Total Files: {task.file_size and 'Multiple files' or '0 files'}
- File Size: {context['file_size_mb']} MB
- Export Date: {task.completed_at.strftime('%Y-%m-%d %H:%M:%S')}

Download Link:
{download_url}

The ZIP file contains all requested files with geometry/entry ID prefixes for easy identification.

Best regards,
ISR Field Team
"""
        
        # Send email
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        print(f"Export completion email sent to {user.email}")
        
    except Exception as e:
        print(f"Failed to send export completion email: {e}")


def start_export_task(dataset_id, user_id, file_types=None, date_from=None, date_to=None, 
                     organize_by='geometry', include_metadata=True):
    """
    Start a new export task.
    
    Returns:
        ExportTask: The created task object
    """
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Create task record
    task = ExportTask.objects.create(
        task_id=task_id,
        dataset_id=dataset_id,
        user_id=user_id,
        file_types=file_types or ['all'],
        date_from=date_from,
        date_to=date_to,
        organize_by=organize_by,
        include_metadata=include_metadata
    )
    
    # Start background task (in a real implementation, you'd use Celery or similar)
    # For now, we'll run it synchronously but in a separate thread
    import threading
    
    def run_export():
        try:
            generate_zip_export(
                task_id=task_id,
                dataset_id=dataset_id,
                user_id=user_id,
                file_types=file_types,
                date_from=date_from,
                date_to=date_to,
                organize_by=organize_by,
                include_metadata=include_metadata
            )
        except Exception as e:
            print(f"Export task failed: {e}")
    
    # Start the task in a separate thread
    thread = threading.Thread(target=run_export)
    thread.daemon = True
    thread.start()
    
    return task
