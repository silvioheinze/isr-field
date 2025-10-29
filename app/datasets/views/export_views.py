"""
Views for exporting dataset files with ZIP export and email notifications.

This module provides web-based file export functionality with:
1. ZIP archive downloads with geometry/entry ID prefixes
2. Email notifications when export is completed
3. Background task processing
4. Task status tracking
"""

import os
import zipfile
import csv
import json
from datetime import datetime
from pathlib import Path
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, JsonResponse, Http404
from django.conf import settings
from django.db.models import Q, Count, Sum
from django.contrib import messages
from django.utils import timezone
from django.core.files.storage import default_storage

from ..models import DataSet, DataEntry, DataEntryFile, ExportTask
from ..tasks import start_export_task


@login_required
def dataset_files_export_view(request, dataset_id):
    """Main export view with options and statistics"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    # Get file statistics
    files_queryset = DataEntryFile.objects.filter(
        entry__geometry__dataset=dataset
    ).select_related('entry', 'entry__geometry', 'upload_user')
    
    stats = calculate_file_statistics(files_queryset)
    
    # Get recent files
    recent_files = files_queryset.order_by('-upload_date')[:10]
    
    return render(request, 'datasets/dataset_files_export.html', {
        'dataset': dataset,
        'stats': stats,
        'recent_files': recent_files,
        'file_types': get_file_type_options(),
        'organize_options': get_organize_options(),
    })


@login_required
def export_files_zip_view(request, dataset_id):
    """Export files as ZIP archive with email notification"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        # Get export parameters from POST data
        file_types = request.POST.getlist('file_types', ['all'])
        date_from = request.POST.get('date_from')
        date_to = request.POST.get('date_to')
        organize_by = request.POST.get('organize_by', 'geometry')
        include_metadata = request.POST.get('include_metadata', 'true').lower() == 'true'
        email_notification = request.POST.get('email_notification', 'true').lower() == 'true'
        
        # Convert date strings to date objects
        date_from_obj = None
        date_to_obj = None
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Invalid date format for start date.')
                return redirect('dataset_files_export', dataset_id=dataset_id)
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Invalid date format for end date.')
                return redirect('dataset_files_export', dataset_id=dataset_id)
        
        # Check if user has email address for notifications
        if email_notification and not request.user.email:
            messages.warning(request, 'Email notification requested but no email address found in your profile.')
            email_notification = False
        
        # Start export task
        try:
            task = start_export_task(
                dataset_id=dataset_id,
                user_id=request.user.id,
                file_types=file_types,
                date_from=date_from_obj,
                date_to=date_to_obj,
                organize_by=organize_by,
                include_metadata=include_metadata
            )
            
            if email_notification:
                messages.success(request, f'Export task started! You will receive an email notification when the ZIP file is ready for download.')
            else:
                messages.success(request, f'Export task started! Please check back in a few minutes for your download.')
            
            return redirect('export_task_status', task_id=task.task_id)
            
        except Exception as e:
            messages.error(request, f'Failed to start export task: {str(e)}')
            return redirect('dataset_files_export', dataset_id=dataset_id)
    
    # GET request - show export form
    return redirect('dataset_files_export', dataset_id=dataset_id)


@login_required
def export_task_status_view(request, task_id):
    """View export task status and download link"""
    task = get_object_or_404(ExportTask, task_id=task_id)
    
    # Check if user has access to this task
    if task.user != request.user:
        return render(request, 'datasets/403.html', status=403)
    
    # Prepare context
    context = {
        'task': task,
        'dataset': task.dataset,
        'download_url': None,
    }
    
    if task.status == 'completed' and task.file_path:
        # Create download URL
        context['download_url'] = f"{settings.MEDIA_URL}{task.file_path}"
        context['file_size_mb'] = round(task.file_size / (1024 * 1024), 2) if task.file_size else 0
    
    return render(request, 'datasets/export_task_status.html', context)


@login_required
def download_export_file_view(request, task_id):
    """Download the completed export file"""
    task = get_object_or_404(ExportTask, task_id=task_id)
    
    # Check if user has access to this task
    if task.user != request.user:
        return render(request, 'datasets/403.html', status=403)
    
    # Check if task is completed
    if task.status != 'completed' or not task.file_path:
        messages.error(request, 'Export file is not ready for download.')
        return redirect('export_task_status', task_id=task_id)
    
    # Check if file exists
    file_path = Path(settings.MEDIA_ROOT) / task.file_path
    if not file_path.exists():
        messages.error(request, 'Export file not found. Please try exporting again.')
        return redirect('dataset_files_export', dataset_id=task.dataset.id)
    
    # Create download response
    response = HttpResponse(content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{task.dataset.name}_files_{task.task_id[:8]}.zip"'
    
    with open(file_path, 'rb') as f:
        response.write(f.read())
    
    return response


def calculate_file_statistics(files_queryset):
    """Calculate comprehensive file statistics"""
    stats = {
        'total_files': files_queryset.count(),
        'total_size': files_queryset.aggregate(total=Sum('file_size'))['total'] or 0,
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


def get_file_type_options():
    """Get available file type filter options"""
    return [
        {'value': 'all', 'label': 'All Files'},
        {'value': 'image', 'label': 'Images Only'},
        {'value': 'document', 'label': 'Documents Only'},
    ]


def get_organize_options():
    """Get available organization options"""
    return [
        {'value': 'geometry', 'label': 'By Geometry ID'},
        {'value': 'entry', 'label': 'By Entry'},
        {'value': 'date', 'label': 'By Upload Date'},
        {'value': 'user', 'label': 'By Upload User'},
        {'value': 'type', 'label': 'By File Type'},
    ]