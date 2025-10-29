from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth import login as auth_login, logout
from django.shortcuts import redirect

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.models import User, Group

from django.shortcuts import get_object_or_404
from django.contrib.auth.forms import UserChangeForm, PasswordChangeForm
from django.contrib.auth.models import Group
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.models import Group
from django import forms
from .models import AuditLog, DataSet, DataGeometry, DataEntry, DataEntryField, DataEntryFile, Typology, TypologyEntry, DatasetFieldConfig, DatasetField
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
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail

# Set up logging for import debugging
logger = logging.getLogger(__name__)

class DatasetFieldConfigForm(forms.ModelForm):
    """Form for configuring dataset field settings"""
    
    class Meta:
        model = DatasetFieldConfig
        fields = [
            'usage_code1_label', 'usage_code1_enabled',
            'usage_code2_label', 'usage_code2_enabled', 
            'usage_code3_label', 'usage_code3_enabled',
            'cat_inno_label', 'cat_inno_enabled',
            'cat_wert_label', 'cat_wert_enabled',
            'cat_fili_label', 'cat_fili_enabled',
            'year_label', 'year_enabled',
            'name_label', 'name_enabled'
        ]
        widgets = {
            'usage_code1_label': forms.TextInput(attrs={'class': 'form-control'}),
            'usage_code1_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'usage_code2_label': forms.TextInput(attrs={'class': 'form-control'}),
            'usage_code2_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'usage_code3_label': forms.TextInput(attrs={'class': 'form-control'}),
            'usage_code3_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cat_inno_label': forms.TextInput(attrs={'class': 'form-control'}),
            'cat_inno_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cat_wert_label': forms.TextInput(attrs={'class': 'form-control'}),
            'cat_wert_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cat_fili_label': forms.TextInput(attrs={'class': 'form-control'}),
            'cat_fili_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'year_label': forms.TextInput(attrs={'class': 'form-control'}),
            'year_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'name_label': forms.TextInput(attrs={'class': 'form-control'}),
            'name_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DatasetFieldForm(forms.ModelForm):
    """Form for creating and editing dataset fields"""
    
    class Meta:
        model = DatasetField
        fields = ['field_name', 'label', 'field_type', 'required', 'enabled', 'help_text', 'choices', 'order', 'is_coordinate_field', 'is_id_field', 'is_address_field', 'typology']
        widgets = {
            'field_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'field_name'}),
            'label': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Display Label'}),
            'field_type': forms.Select(attrs={'class': 'form-select'}),
            'required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'help_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'choices': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Option 1, Option 2, Option 3'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_coordinate_field': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_id_field': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_address_field': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'typology': forms.Select(attrs={'class': 'form-select'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate typology choices
        self.fields['typology'].queryset = Typology.objects.all().order_by('name')
        self.fields['typology'].empty_label = "No typology selected"
    
    def clean_field_name(self):
        """Validate field name"""
        field_name = self.cleaned_data.get('field_name')
        if field_name:
            # Convert to lowercase and replace spaces with underscores
            field_name = field_name.lower().replace(' ', '_')
            # Remove any non-alphanumeric characters except underscores
            import re
            field_name = re.sub(r'[^a-z0-9_]', '', field_name)
            # Ensure it starts with a letter
            if field_name and not field_name[0].isalpha():
                field_name = 'field_' + field_name
        return field_name
    
    def clean_choices(self):
        """Validate choices for choice fields"""
        choices = self.cleaned_data.get('choices')
        field_type = self.cleaned_data.get('field_type')
        
        if field_type == 'choice' and not choices:
            raise forms.ValidationError("Choices are required for choice fields.")
        
        return choices


class DatasetFieldInlineFormSet(forms.BaseInlineFormSet):
    """Formset for managing multiple dataset fields"""
    
    def clean(self):
        """Validate the formset"""
        if any(self.errors):
            return
        
        names = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                name = form.cleaned_data.get('name')
                if name in names:
                    raise forms.ValidationError(f"Field name '{name}' is duplicated.")
                names.append(name)

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


def password_reset_view(request):
    """Custom password reset form view"""
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            associated_users = User.objects.filter(email=email)
            if associated_users.exists():
                for user in associated_users:
                    subject = "Password Reset Request - ISR Field"
                    email_template_name = "datasets/password_reset_email.html"
                    c = {
                        "email": user.email,
                        'domain': get_current_site(request).domain,
                        'site_name': 'ISR Field',
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "user": user,
                        'token': default_token_generator.make_token(user),
                        'protocol': 'https' if request.is_secure() else 'http',
                    }
                    email = render_to_string(email_template_name, c)
                    try:
                        send_mail(subject, email, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
                    except Exception as e:
                        messages.error(request, f'Error sending email: {str(e)}')
                        return render(request, 'datasets/password_reset_form.html', {'form': form})
                    
                    messages.success(request, 'Password reset email has been sent. Please check your email.')
                    return redirect('password_reset_done')
            else:
                # Don't reveal if email exists or not for security
                messages.success(request, 'Password reset email has been sent. Please check your email.')
                return redirect('password_reset_done')
    else:
        form = PasswordResetForm()
    return render(request, 'datasets/password_reset_form.html', {'form': form})


def password_reset_done_view(request):
    """Password reset done view"""
    return render(request, 'datasets/password_reset_done.html')


def password_reset_confirm_view(request, uidb64, token):
    """Password reset confirm view"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your password has been successfully reset.')
                return redirect('password_reset_complete')
        else:
            form = SetPasswordForm(user)
        return render(request, 'datasets/password_reset_confirm.html', {'form': form})
    else:
        messages.error(request, 'The password reset link is invalid or has expired.')
        return redirect('password_reset_form')


def password_reset_complete_view(request):
    """Password reset complete view"""
    return render(request, 'datasets/password_reset_complete.html')

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


def detect_csv_delimiter(csv_content, sample_size=1024):
    """
    Detect the delimiter used in a CSV file by analyzing the first few lines.
    Returns the most likely delimiter character.
    """
    # Take a sample of the content for analysis
    sample = csv_content[:sample_size]
    lines = sample.split('\n')[:5]  # Analyze first 5 lines
    
    if not lines or not lines[0].strip():
        return ','  # Default to comma if no content
    
    # Common delimiters to test
    delimiters = [',', ';', '\t', '|']
    delimiter_scores = {}
    
    for delimiter in delimiters:
        score = 0
        for line in lines:
            if not line.strip():
                continue
                
            # Count occurrences of this delimiter
            count = line.count(delimiter)
            if count > 0:
                # Score based on consistency across lines
                score += count
                
                # Bonus for having the same number of delimiters in each line
                if len([l for l in lines if l.count(delimiter) == count]) > 1:
                    score += 2
                    
                # Bonus for having reasonable number of columns (not too few, not too many)
                if 2 <= count <= 20:
                    score += 1
                    
        delimiter_scores[delimiter] = score
    
    # Find the delimiter with the highest score
    best_delimiter = max(delimiter_scores, key=delimiter_scores.get)
    
    # If no delimiter scored well, default to comma
    if delimiter_scores[best_delimiter] == 0:
        best_delimiter = ','
    
    logger.info(f"CSV delimiter detection: {delimiter_scores}, selected: '{best_delimiter}'")
    return best_delimiter

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
    
    return render(request, 'datasets/dashboard.html', {
        'datasets': accessible_datasets[:5],  # Show first 5 datasets
        'can_create_datasets': is_manager(request.user),
        'can_create_typologies': is_manager(request.user)
    })


def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'datasets/register.html', {'form': form})


@login_required
def logout_view(request):
    """Custom logout view that handles both GET and POST requests"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')


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
    
    return render(request, 'datasets/profile.html', {
        'user': user,
        'password_form': password_form,
        'message': message,
        'message_type': message_type
    })


def is_manager(user):
    return user.is_authenticated and (user.is_superuser or user.is_staff)

@login_required
def user_management_view(request):
    if not is_manager(request.user):
        return render(request, 'datasets/403.html', status=403)
    users = User.objects.all()
    groups = Group.objects.all()
    return render(request, 'datasets/user_management.html', {'users': users, 'groups': groups})

@login_required
def edit_user_view(request, user_id):
    if not is_manager(request.user):
        return render(request, 'datasets/403.html', status=403)
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        # Handle form submission
        email = request.POST.get('email')
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        group_ids = request.POST.getlist('groups')
        
        # Update user fields
        user.email = email
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.save()
        
        # Update groups
        user.groups.set(Group.objects.filter(id__in=group_ids))
        
        # Debug: Print the values to see what's being saved
        print(f"POST data: {request.POST}")
        print(f"Email: {email}")
        print(f"is_staff: {is_staff}")
        print(f"is_superuser: {is_superuser}")
        print(f"group_ids: {group_ids}")
        print(f"Final user.is_staff: {user.is_staff}")
        print(f"Final user.is_superuser: {user.is_superuser}")
        
        messages.success(request, 'User updated successfully.')
        return redirect('user_management')
    else:
        # Create form for display
        form = UserChangeForm(instance=user)
    
    all_groups = Group.objects.all()
    user_groups = user.groups.values_list('id', flat=True)
    return render(request, 'datasets/edit_user.html', {'form': form, 'user_obj': user, 'all_groups': all_groups, 'user_groups': user_groups})

@login_required
def delete_user_view(request, user_id):
    if not is_manager(request.user):
        return render(request, 'datasets/403.html', status=403)
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('user_management')
    return render(request, 'datasets/delete_user.html', {'user_obj': user})

@login_required
def create_user_view(request):
    if not is_manager(request.user):
        return render(request, 'datasets/403.html', status=403)
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
    return render(request, 'datasets/create_user.html', {'form': form, 'all_groups': all_groups})

@login_required
def create_group_view(request):
    if not is_manager(request.user):
        return render(request, 'datasets/403.html', status=403)
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Group created successfully.')
            return redirect('user_management')
    else:
        form = GroupForm()
    return render(request, 'datasets/create_group.html', {'form': form})

@login_required
def modify_user_groups_view(request, user_id):
    if not is_manager(request.user):
        return render(request, 'datasets/403.html', status=403)
    user = get_object_or_404(User, pk=user_id)
    all_groups = Group.objects.all()
    if request.method == 'POST':
        group_ids = request.POST.getlist('groups')
        user.groups.set(Group.objects.filter(id__in=group_ids))
        messages.success(request, 'User groups updated successfully.')
        return redirect('user_management')
    user_groups = user.groups.values_list('id', flat=True)
    return render(request, 'datasets/modify_user_groups.html', {'user_obj': user, 'all_groups': all_groups, 'user_groups': user_groups})

@login_required
def edit_group_view(request, group_id):
    """Edit group name and manage group members"""
    if not is_manager(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    group = get_object_or_404(Group, pk=group_id)
    all_users = User.objects.all().order_by('username')
    
    if request.method == 'POST':
        # Update group name
        new_name = request.POST.get('name', '').strip()
        if new_name and new_name != group.name:
            group.name = new_name
            group.save()
            messages.success(request, f'Group name updated to "{new_name}".')
        
        # Update group members
        user_ids = request.POST.getlist('users')
        group.user_set.set(User.objects.filter(id__in=user_ids))
        
        messages.success(request, f'Group "{group.name}" members updated successfully.')
        return redirect('user_management')
    
    # Get current group members
    group_members = group.user_set.values_list('id', flat=True)
    
    return render(request, 'datasets/edit_group.html', {
        'group': group,
        'all_users': all_users,
        'group_members': group_members
    })

@login_required
def dataset_list_view(request):
    """List datasets that the user can access"""
    accessible_datasets = []
    for dataset in DataSet.objects.all():
        if dataset.can_access(request.user):
            accessible_datasets.append(dataset)
    return render(request, 'datasets/dataset_list.html', {
        'datasets': accessible_datasets,
        'can_create_datasets': is_manager(request.user)
    })

@login_required
def dataset_create_view(request):
    """Create a new dataset"""
    if not is_manager(request.user):
        return render(request, 'datasets/403.html', status=403)
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
    
    return render(request, 'datasets/dataset_create.html')

@login_required
def dataset_detail_view(request, dataset_id):
    """View dataset details"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
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
        'can_create_typologies': is_manager(request.user),
        'all_fields': all_fields
    })

@login_required
def custom_field_create_view(request, dataset_id):
    """Create a new custom field for a dataset (only owner can create)"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if dataset.owner != request.user:
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        form = DatasetFieldForm(request.POST)
        if form.is_valid():
            custom_field = form.save(commit=False)
            custom_field.dataset = dataset
            # This is a custom field
            custom_field.save()
            messages.success(request, f'Custom field "{custom_field.label}" created successfully.')
            return redirect('dataset_detail', dataset_id=dataset.id)
    else:
        form = DatasetFieldForm()
    
    return render(request, 'datasets/custom_field_form.html', {
        'dataset': dataset,
        'form': form,
        'title': 'Create Custom Field'
    })

@login_required
def custom_field_edit_view(request, dataset_id, field_id):
    """Edit a custom field (only owner can edit)"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if dataset.owner != request.user:
        return render(request, 'datasets/403.html', status=403)
    
    custom_field = get_object_or_404(DatasetField, pk=field_id, dataset=dataset)
    
    if request.method == 'POST':
        form = DatasetFieldForm(request.POST, instance=custom_field)
        if form.is_valid():
            form.save()
            messages.success(request, f'Custom field "{custom_field.label}" updated successfully.')
            return redirect('dataset_detail', dataset_id=dataset.id)
    else:
        form = DatasetFieldForm(instance=custom_field)
    
    return render(request, 'datasets/custom_field_form.html', {
        'dataset': dataset,
        'form': form,
        'title': 'Edit Custom Field',
        'custom_field': custom_field
    })

@login_required
def custom_field_delete_view(request, dataset_id, field_id):
    """Delete a custom field (only owner can delete)"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if dataset.owner != request.user:
        return render(request, 'datasets/403.html', status=403)
    
    custom_field = get_object_or_404(DatasetField, pk=field_id, dataset=dataset)
    
    if request.method == 'POST':
        field_name = custom_field.label
        custom_field.delete()
        messages.success(request, f'Custom field "{field_name}" deleted successfully.')
        return redirect('dataset_detail', dataset_id=dataset.id)
    
    return render(request, 'datasets/custom_field_delete.html', {
        'dataset': dataset,
        'custom_field': custom_field
    })


@login_required
def dataset_edit_view(request, dataset_id):
    """Edit dataset (only owner can edit)"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if dataset.owner != request.user:
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'delete':
            # Handle dataset deletion
            dataset_name = dataset.name
            dataset_id = dataset.id
            
            # Log the action before deletion
            AuditLog.objects.create(
                user=request.user,
                action='deleted_dataset',
                target=f'dataset:{dataset_id}'
            )
            
            # Delete the dataset (this will cascade delete all related data)
            dataset.delete()
            
            messages.success(request, f'Dataset "{dataset_name}" has been deleted successfully.')
            return redirect('dataset_list')
        else:
            # Handle dataset update
            dataset.name = request.POST.get('name')
            dataset.description = request.POST.get('description', '')
            dataset.is_public = request.POST.get('is_public') == 'on'
            
            # Handle allow_multiple_entries field (might not exist if migration not applied)
            try:
                dataset.allow_multiple_entries = request.POST.get('allow_multiple_entries') == 'on'
            except AttributeError:
                pass  # Field doesn't exist yet, skip it
            
            dataset.save()
            
            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action='edited_dataset',
                target=f'dataset:{dataset.id}'
            )
            
            messages.success(request, 'Dataset updated successfully.')
            return redirect('dataset_detail', dataset_id=dataset.id)
    
    return render(request, 'datasets/dataset_edit.html', {'dataset': dataset})

@login_required
def dataset_access_view(request, dataset_id):
    """Manage dataset access (only owner can manage access)"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if dataset.owner != request.user:
        return render(request, 'datasets/403.html', status=403)
    
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
            'field_type': field.field_type,
            'field_name': field.field_name,
            'required': field.required,
            'enabled': field.enabled,
            'help_text': field.help_text or '',
            'choices': field.choices or '',
            'order': field.order,
            'typology_choices': field.get_choices_list() if field.field_type == 'choice' else []
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
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    # Get all geometries with their entries
    geometries = DataGeometry.objects.filter(dataset=dataset).prefetch_related('entries__fields').order_by('id_kurz')
    
    # Get all enabled fields for this dataset
    all_fields = DatasetField.objects.filter(dataset=dataset, enabled=True).order_by('order', 'field_name')
    
    # Prepare entries data
    entries_data = []
    for geometry in geometries:
        for entry in geometry.entries.all():
            entry_data = {
                'id': entry.id,
                'geometry_id': geometry.id,
                'id_kurz': geometry.id_kurz,
                'address': geometry.address,
                'entry_name': entry.name,
                'year': entry.year,
                'user': entry.user.username if entry.user else 'Unknown',
                'created_at': entry.created_at,
                'fields': {}
            }
            
            # Add field values
            for field in entry.fields.all():
                entry_data['fields'][field.field_name] = field.get_typed_value()
            
            entries_data.append(entry_data)
    
    # Handle search/filtering
    search_query = request.GET.get('search', '')
    if search_query:
        entries_data = [entry for entry in entries_data 
                       if search_query.lower() in entry['id_kurz'].lower() 
                       or search_query.lower() in entry['address'].lower()
                       or search_query.lower() in (entry['entry_name'] or '').lower()]
    
    # Handle sorting
    sort_by = request.GET.get('sort', 'id_kurz')
    reverse = request.GET.get('order', 'asc') == 'desc'
    
    if sort_by in ['id_kurz', 'address', 'entry_name', 'year', 'user']:
        entries_data.sort(key=lambda x: x[sort_by] or '', reverse=reverse)
    elif sort_by.startswith('field_'):
        field_name = sort_by[6:]  # Remove 'field_' prefix
        entries_data.sort(key=lambda x: str(x['fields'].get(field_name, '')), reverse=reverse)
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(entries_data, 25)  # 25 entries per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'datasets/dataset_entries_table.html', {
        'dataset': dataset,
        'all_fields': all_fields,
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
        'order': 'desc' if reverse else 'asc'
    })


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


@login_required
def dataset_clear_data_view(request, dataset_id):
    """Clear all geometry points and data entries from a dataset"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    
    # Only dataset owner can clear data
    if dataset.owner != request.user:
        return render(request, 'datasets/403.html', status=403)
    
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
    
    return render(request, 'datasets/dataset_clear_data.html', {
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
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        # Update direct fields
        entry.name = request.POST.get('name', '')
        year_value = request.POST.get('year', '')
        if year_value:
            try:
                entry.year = int(year_value)
            except ValueError:
                entry.year = None
        else:
            entry.year = None
        entry.save()
        
        # Update dynamic fields
        for field in entry.fields.all():
            field_value = request.POST.get(field.field_name, '')
            if field_value:
                # Convert value based on field type
                if field.field_type == 'integer':
                    try:
                        typed_value = int(field_value)
                    except ValueError:
                        typed_value = 0
                elif field.field_type == 'decimal':
                    try:
                        typed_value = float(field_value)
                    except ValueError:
                        typed_value = 0.0
                else:
                    typed_value = field_value
                
                field.value = str(typed_value)
                field.save()
            else:
                # Remove field if no value provided
                field.delete()
        
        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='edited_entry',
            target=f'entry:{entry.id}'
        )
        
        messages.success(request, 'Entry updated successfully.')
        return redirect('dataset_data_input', dataset_id=dataset.id)
    
    # Get all fields for this dataset
    all_fields = DatasetField.objects.filter(dataset=dataset).order_by('order', 'field_name')
    
    return render(request, 'datasets/entry_edit.html', {
        'entry': entry,
        'all_fields': all_fields
    })

@login_required
def entry_create_view(request, geometry_id):
    """Create a new DataEntry for a specific geometry"""
    geometry = get_object_or_404(DataGeometry, pk=geometry_id)
    dataset = geometry.dataset
    
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
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
            
            # Get all enabled fields for this dataset
            all_fields = DatasetField.objects.filter(dataset=dataset, enabled=True)
            
            # Prepare entry data
            entry_data = {
                'geometry': geometry,
                'user': request.user
            }
            
            # Handle special fields (name, year)
            entry_data['name'] = request.POST.get('name', '')
            year_value = request.POST.get('year', '')
            if year_value:
                try:
                    entry_data['year'] = int(year_value)
                except ValueError:
                    entry_data['year'] = None
            
            # Create the entry
            entry = DataEntry.objects.create(**entry_data)
            
            # Handle all other fields as dynamic fields
            for field in all_fields:
                if field.field_name not in ['name', 'year']:  # Skip special fields
                    field_value = request.POST.get(field.field_name)
                    if field_value:
                        # Convert value based on field type
                        if field.field_type == 'integer':
                            try:
                                typed_value = int(field_value)
                            except ValueError:
                                typed_value = 0
                        elif field.field_type == 'decimal':
                            try:
                                typed_value = float(field_value)
                            except ValueError:
                                typed_value = 0.0
                        else:
                            typed_value = field_value
                        
                        # Store as dynamic field
                        entry.set_field_value(field.field_name, str(typed_value), field.field_type)
            
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
            target=f'entry:{entry.id}'
        except Exception as e:
            # Debug logging
            print(f"Error creating entry: {str(e)}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": str(e)}, status=400)
            else:
                messages.error(request, f"Error creating entry: {str(e)}")
                return redirect("dataset_data_input", dataset_id=dataset.id)
        
            # Check if this is an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'entry_id': entry.id})
            else:
                messages.success(request, 'Entry created successfully.')
                return redirect('dataset_data_input', dataset_id=dataset.id)

@login_required
def geometry_create_view(request, dataset_id):
    """Create a new geometry point for a dataset"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
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
    
    return render(request, 'datasets/geometry_create.html', {'dataset': dataset})

@login_required
def file_upload_view(request, entry_id):
    """Upload files for a DataEntry"""
    entry = get_object_or_404(DataEntry, pk=entry_id)
    geometry = entry.geometry
    dataset = geometry.dataset
    
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
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
    
    return render(request, 'datasets/file_upload.html', {'entry': entry})

@login_required
def file_download_view(request, file_id):
    """Download a file"""
    entry_file = get_object_or_404(DataEntryFile, pk=file_id)
    entry = entry_file.entry
    geometry = entry.geometry
    dataset = geometry.dataset
    
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
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
        return render(request, 'datasets/403.html', status=403)
    
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
    
    return render(request, 'datasets/file_delete.html', {'entry_file': entry_file})

@login_required
def entry_detail_view(request, entry_id):
    """Detailed view of a DataEntry with its files"""
    entry = get_object_or_404(DataEntry, pk=entry_id)
    geometry = entry.geometry
    dataset = geometry.dataset
    
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    # Debug: Print file information
    print(f"Entry {entry_id} has {entry.files.count()} files")
    for file in entry.files.all():
        print(f"File: {file.filename}, URL: {file.file.url}, Path: {file.file.path}")
        print(f"File exists: {os.path.exists(file.file.path)}")
    
    return render(request, 'datasets/entry_detail.html', {'entry': entry})


@login_required
def dataset_csv_column_selection_view(request, dataset_id):
    """Show CSV column selection form"""
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if not dataset.can_access(request.user):
        logger.warning(f"User {request.user.username} attempted to access dataset {dataset_id} without permission")
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, 'Please select a CSV file to import.')
            return render(request, 'datasets/dataset_csv_import.html', {'dataset': dataset})
        
        csv_file = request.FILES['csv_file']
        
        # Check file extension
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a valid CSV file.')
            return render(request, 'datasets/dataset_csv_import.html', {'dataset': dataset})
        
        try:
            # Read CSV file to get headers
            decoded_file = csv_file.read().decode('utf-8')
            
            # Detect CSV delimiter
            delimiter = detect_csv_delimiter(decoded_file)
            logger.info(f"Detected CSV delimiter: '{delimiter}'")
            logger.info(f"File size: {len(decoded_file)} characters")
            logger.info(f"First 200 chars: {decoded_file[:200]}")
            
            csv_data = csv.DictReader(io.StringIO(decoded_file), delimiter=delimiter)
            headers = csv_data.fieldnames
            logger.info(f"Headers detected: {headers}")
            logger.info(f"Number of headers: {len(headers) if headers else 0}")
            
            if not headers:
                messages.error(request, 'CSV file appears to be empty or invalid.')
                return render(request, 'datasets/dataset_csv_import.html', {'dataset': dataset})
            
            # Store the CSV file temporarily in session for the next step
            request.session['csv_file_content'] = decoded_file
            request.session['csv_file_name'] = csv_file.name
            request.session['csv_delimiter'] = delimiter
            
            # Show column selection form
            return render(request, 'datasets/dataset_csv_column_selection.html', {
                'dataset': dataset,
                'headers': headers,
                'detected_delimiter': delimiter
            })
            
        except Exception as e:
            logger.error(f"Error reading CSV file: {str(e)}", exc_info=True)
            messages.error(request, f'Error reading CSV file: {str(e)}')
            return render(request, 'datasets/dataset_csv_import.html', {'dataset': dataset})
    
    return render(request, 'datasets/dataset_csv_import.html', {'dataset': dataset})


@login_required
def dataset_csv_import_view(request, dataset_id):
    """Import CSV data into a dataset with column selection"""
    logger.info(f"Starting CSV import for dataset {dataset_id} by user {request.user.username}")
    
    dataset = get_object_or_404(DataSet, pk=dataset_id)
    if not dataset.can_access(request.user):
        logger.warning(f"User {request.user.username} attempted to access dataset {dataset_id} without permission")
        return render(request, 'datasets/403.html', status=403)
    
    if request.method == 'POST':
        logger.info("Processing POST request for CSV import")
        
        # Check if this is a column selection form submission
        if 'id_column' in request.POST:
            # This is the column selection form submission
            id_column = request.POST.get('id_column')
            coordinate_system = request.POST.get('coordinate_system', 'auto')
            
            # Get CSV content from session
            if 'csv_file_content' not in request.session:
                messages.error(request, 'CSV file session expired. Please upload the file again.')
                return render(request, 'datasets/dataset_csv_import.html', {'dataset': dataset})
            
            decoded_file = request.session['csv_file_content']
            csv_file_name = request.session.get('csv_file_name', 'unknown.csv')
            
            logger.info(f"Processing CSV with ID column: {id_column}, coordinate system: {coordinate_system}")
            
            try:
                # Process the CSV with selected columns
                return process_csv_import(request, dataset, decoded_file, csv_file_name, id_column, coordinate_system)
            except Exception as e:
                logger.error(f"Error processing CSV import: {str(e)}", exc_info=True)
                messages.error(request, f'Error processing CSV file: {str(e)}')
                return render(request, 'datasets/dataset_csv_import.html', {'dataset': dataset})
        
        # Original file upload logic - redirect to column selection
        if 'csv_file' not in request.FILES:
            logger.error("No CSV file found in request.FILES")
            logger.debug(f"Available files in request.FILES: {list(request.FILES.keys())}")
            messages.error(request, 'Please select a CSV file to import.')
            return render(request, 'datasets/dataset_csv_import.html', {'dataset': dataset})
        
        csv_file = request.FILES['csv_file']
        logger.info(f"CSV file received: {csv_file.name}, size: {csv_file.size} bytes")
        
        # Check file extension
        if not csv_file.name.endswith('.csv'):
            logger.error(f"Invalid file type: {csv_file.name}")
            messages.error(request, 'Please upload a valid CSV file.')
            return render(request, 'datasets/dataset_csv_import.html', {'dataset': dataset})
        
        try:
            # Read CSV file to get headers
            decoded_file = csv_file.read().decode('utf-8')
            
            # Detect CSV delimiter
            delimiter = detect_csv_delimiter(decoded_file)
            logger.info(f"Detected CSV delimiter: '{delimiter}'")
            logger.info(f"File size: {len(decoded_file)} characters")
            logger.info(f"First 200 chars: {decoded_file[:200]}")
            
            csv_data = csv.DictReader(io.StringIO(decoded_file), delimiter=delimiter)
            headers = csv_data.fieldnames
            logger.info(f"Headers detected: {headers}")
            logger.info(f"Number of headers: {len(headers) if headers else 0}")
            
            if not headers:
                messages.error(request, 'CSV file appears to be empty or invalid.')
                return render(request, 'datasets/dataset_csv_import.html', {'dataset': dataset})
            
            # Store the CSV file temporarily in session for the next step
            request.session['csv_file_content'] = decoded_file
            request.session['csv_file_name'] = csv_file.name
            request.session['csv_delimiter'] = delimiter
            
            # Show column selection form
            return render(request, 'datasets/dataset_csv_column_selection.html', {
                'dataset': dataset,
                'headers': headers,
                'detected_delimiter': delimiter
            })
            
        except Exception as e:
            logger.error(f"Error reading CSV file: {str(e)}", exc_info=True)
            messages.error(request, f'Error reading CSV file: {str(e)}')
            return render(request, 'datasets/dataset_csv_import.html', {'dataset': dataset})
    
    return render(request, 'datasets/dataset_csv_import.html', {'dataset': dataset})


def process_csv_import(request, dataset, decoded_file, csv_file_name, id_column, coordinate_system):
    """Process CSV import with selected columns"""
    logger.info(f"Processing CSV import with ID column: {id_column}")
    
    try:
        # Read CSV file
        logger.info("Reading CSV file content")
        logger.debug(f"CSV content length: {len(decoded_file)} characters")
        
        # Get delimiter from session or detect it
        delimiter = request.session.get('csv_delimiter', ',')
        logger.info(f"Using CSV delimiter: '{delimiter}'")
        
        csv_data = csv.DictReader(io.StringIO(decoded_file), delimiter=delimiter)
        logger.info(f"CSV headers detected: {csv_data.fieldnames}")
        
        imported_count = 0
        errors = []
        
        with transaction.atomic():
            logger.info("Starting transaction for CSV import")
            
            # First, create DatasetField entries for all columns (except coordinate and ID columns)
            logger.info("Creating DatasetField entries for CSV columns")
            coordinate_columns = {'GEB_X', 'GEB_Y', 'X', 'Y', 'LONGITUDE', 'LATITUDE', 'LON', 'LAT'}
            excluded_columns = {id_column} | coordinate_columns
            
            # Get all unique column names from the CSV
            csv_data_list = list(csv.DictReader(io.StringIO(decoded_file), delimiter=delimiter))
            all_columns = set()
            for row in csv_data_list:
                all_columns.update(row.keys())
            
            # Create DatasetField entries for columns that aren't excluded
            field_order = 0
            for column_name in sorted(all_columns):
                if column_name not in excluded_columns:
                    # Check if field already exists
                    existing_field = DatasetField.objects.filter(
                        dataset=dataset, 
                        field_name=column_name
                    ).first()
                    
                    if not existing_field:
                        # Determine field type based on sample values
                        field_type = 'text'  # default
                        sample_values = [row.get(column_name, '') for row in csv_data_list[:10] if row.get(column_name, '').strip()]
                        
                        if sample_values:
                            # Try to determine type from sample values
                            is_integer = True
                            is_decimal = True
                            for value in sample_values:
                                if value.strip():
                                    try:
                                        int(value)
                                    except ValueError:
                                        is_integer = False
                                    try:
                                        float(value)
                                    except ValueError:
                                        is_decimal = False
                            
                            if is_integer:
                                field_type = 'integer'
                            elif is_decimal:
                                field_type = 'decimal'
                        
                        DatasetField.objects.create(
                            dataset=dataset,
                            field_name=column_name,
                            label=column_name.replace('_', ' ').title(),
                            field_type=field_type,
                            required=False,
                            enabled=True,
                            order=field_order
                        )
                        field_order += 1
                        logger.info(f"Created DatasetField for column: {column_name} (type: {field_type})")
            
            row_count = 0
            for row_num, row in enumerate(csv_data_list, start=2):  # Start at 2 because row 1 is header
                row_count += 1
                logger.debug(f"Processing row {row_num}: {row}")
                try:
                    # Extract data from CSV row using selected ID column
                    id_kurz = row.get(id_column, '').strip()
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
                    
                    # Create geometry point
                    logger.debug(f"Creating geometry point for row {row_num}: ID={id_kurz}, Address={address}, Coordinates=({x_coord}, {y_coord})")
                    try:
                        from django.contrib.gis.geos import Point
                        geometry = DataGeometry.objects.create(
                            dataset=dataset,
                            address=address,
                            id_kurz=id_kurz,
                            geometry=Point(x_coord, y_coord, srid=4326),
                            user=request.user
                        )
                        logger.debug(f"Successfully created geometry with ID: {geometry.id}")
                        
                        # Create data entries for each year found in the CSV
                        years_found = set()
                        for column_name in row.keys():
                            # Look for year-prefixed columns (e.g., 2016_NUTZUNG, 2022_CAT_INNO)
                            if '_' in column_name:
                                try:
                                    year_part = column_name.split('_')[0]
                                    year = int(year_part)
                                    if 1900 <= year <= 2100:  # Reasonable year range
                                        years_found.add(year)
                                except ValueError:
                                    pass
                        
                        # If no years found, create a single entry with current year
                        if not years_found:
                            years_found.add(2024)  # Default year
                        
                        # Create entries for each year
                        for year in years_found:
                            entry = DataEntry.objects.create(
                                geometry=geometry,
                                name=id_kurz,  # Use ID as default name
                                year=year,
                                user=request.user
                            )
                            
                            # Add all CSV columns as dynamic fields for this entry
                            for column_name, value in row.items():
                                if value and value.strip():  # Only add non-empty values
                                    # Determine field type based on value
                                    field_type = 'text'
                                    try:
                                        int(value)
                                        field_type = 'integer'
                                    except ValueError:
                                        try:
                                            float(value)
                                            field_type = 'decimal'
                                        except ValueError:
                                            field_type = 'text'
                                    
                                    entry.set_field_value(column_name, value.strip(), field_type)
                            
                            logger.debug(f"Created entry {entry.id} for year {year}")
                        
                        imported_count += 1
                    except Exception as e:
                        logger.error(f"Row {row_num}: Failed to create geometry: {str(e)}")
                        errors.append(f"Row {row_num}: Failed to create geometry - {str(e)}")
                        continue
                    
                except Exception as e:
                    logger.error(f"Row {row_num}: Error processing row: {str(e)}")
                    errors.append(f"Row {row_num}: Error processing row - {str(e)}")
                    continue
            
            logger.info(f"CSV import completed. Imported: {imported_count}, Errors: {len(errors)}")
            
        # Clear session data
        if 'csv_file_content' in request.session:
            del request.session['csv_file_content']
        if 'csv_file_name' in request.session:
            del request.session['csv_file_name']
        if 'csv_delimiter' in request.session:
            del request.session['csv_delimiter']
            
            # Show results
            if errors:
                messages.warning(request, f'Import completed with {len(errors)} errors. {imported_count} geometries were imported successfully.')
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
    
    return render(request, 'datasets/debug_import.html', {'dataset': dataset})


@login_required
def dataset_export_options_view(request, dataset_id):
    """Show export options for a dataset"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    # Get dataset statistics
    geometries_count = DataGeometry.objects.filter(dataset=dataset).count()
    data_entries_count = DataEntry.objects.filter(geometry__dataset=dataset).count()
    
    return render(request, 'datasets/dataset_export.html', {
        'dataset': dataset,
        'geometries_count': geometries_count,
        'data_entries_count': data_entries_count
    })


@login_required
def dataset_csv_export_view(request, dataset_id):
    """Export dataset as CSV with each geometry as a row and entries as columns named by years"""
    dataset = get_object_or_404(DataSet, id=dataset_id)
    
    # Check if user has access to this dataset
    if not dataset.can_access(request.user):
        return render(request, 'datasets/403.html', status=403)
    
    # Get all geometries for this dataset
    geometries = DataGeometry.objects.filter(dataset=dataset).order_by('id_kurz')
    
    if not geometries.exists():
        messages.warning(request, 'No geometries found in this dataset.')
        return redirect('dataset_detail', dataset_id=dataset.id)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{dataset.name}_export.csv"'
    
    writer = csv.writer(response)
    
    # Get all unique years from data entries
    years = sorted(DataEntry.objects.filter(geometry__dataset=dataset).values_list('year', flat=True).distinct())
    
    # Create header row
    header = ['ID', 'ADRESSE', 'LONGITUDE', 'LATITUDE']
    for year in years:
        header.extend([f'{year}_NUTZUNG', f'{year}_CAT_INNO', f'{year}_CAT_WERT', f'{year}_CAT_FILI', f'{year}_NUTZUNG_NAME'])
    
    writer.writerow(header)
    
    # Write data rows
    for geometry in geometries:
        row = [geometry.id_kurz, geometry.address, geometry.geometry.x, geometry.geometry.y]
        
        # Get entries for this geometry
        entries = DataEntry.objects.filter(geometry=geometry).order_by('year')
        entries_by_year = {entry.year: entry for entry in entries}
        
        for year in years:
            entry = entries_by_year.get(year)
            if entry:
                # Get custom field values
                nutzung = getattr(entry, 'custom_field_1', '') if hasattr(entry, 'custom_field_1') else ''
                cat_inno = getattr(entry, 'custom_field_2', '') if hasattr(entry, 'custom_field_2') else ''
                cat_wert = getattr(entry, 'custom_field_3', '') if hasattr(entry, 'custom_field_3') else ''
                cat_fili = getattr(entry, 'custom_field_4', '') if hasattr(entry, 'custom_field_4') else ''
                nutzung_name = entry.name or ''
                
                row.extend([nutzung, cat_inno, cat_wert, cat_fili, nutzung_name])
            else:
                row.extend(['', '', '', '', ''])
        
        writer.writerow(row)
    
    return response


@login_required
def typology_create_view(request):
    """Create a new typology"""
    if not is_manager(request.user):
        return render(request, 'datasets/403.html', status=403)
    if request.method == 'POST':
        name = request.POST.get('name')
        if not name:
            messages.error(request, 'Typology name is required.')
            return render(request, 'datasets/typology_create.html', {'form': {'name': {'errors': ['This field is required.']}}})
        
        # Create the typology
        typology = Typology.objects.create(name=name, created_by=request.user)
        messages.success(request, f'Typology "{name}" created successfully.')
        return redirect('typology_detail', typology_id=typology.id)
    
    return render(request, 'datasets/typology_create.html')


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
        if not name:
            messages.error(request, 'Typology name is required.')
            return render(request, 'datasets/typology_edit.html', {'typology': typology})
        
        typology.name = name
        typology.save()
        messages.success(request, f'Typology "{name}" updated successfully.')
        return redirect('typology_detail', typology_id=typology.id)
    
    return render(request, 'datasets/typology_edit.html', {'typology': typology})


@login_required
def typology_list_view(request):
    """List all typologies"""
    typologies = Typology.objects.all().order_by('-created_at')
    
    return render(request, 'datasets/typology_list.html', {
        'typologies': typologies,
        'can_create_typologies': is_manager(request.user)
    })


@login_required
def typology_detail_view(request, typology_id):
    """View typology details"""
    typology = get_object_or_404(Typology, pk=typology_id)
    entries = typology.entries.all().order_by('code')
    datasets = typology.datasets.all()
    
    return render(request, 'datasets/typology_detail.html', {
        'typology': typology,
        'entries': entries,
        'datasets': datasets
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
        if not csv_file:
            messages.error(request, 'Please select a CSV file.')
            return render(request, 'datasets/typology_import.html', {'typology': typology})
        
        try:
            # Read CSV file
            decoded_file = csv_file.read().decode('utf-8')
            
            # Detect CSV delimiter
            delimiter = detect_csv_delimiter(decoded_file)
            logger.info(f"Detected CSV delimiter for typology import: '{delimiter}'")
            
            csv_data = csv.reader(io.StringIO(decoded_file), delimiter=delimiter)
            
            # Skip header if requested
            skip_header = request.POST.get('skip_header') == 'on'
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
                    # Update existing entry
                    existing_entry.category = category.strip()
                    existing_entry.name = name.strip()
                    existing_entry.save()
                    updated_count += 1
                else:
                    # Create new entry
                    TypologyEntry.objects.create(
                        typology=typology,
                        code=code,
                        category=category.strip(),
                        name=name.strip()
                    )
                    imported_count += 1
            
            # Show results
            if errors:
                messages.warning(request, f'Import completed with {len(errors)} errors. {imported_count} entries imported, {updated_count} updated.')
            else:
                messages.success(request, f'Successfully imported {imported_count} entries and updated {updated_count} existing entries.')
            
            return redirect('typology_detail', typology_id=typology.id)
            
        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')
            return render(request, 'datasets/typology_import.html', {'typology': typology})
    
    return render(request, 'datasets/typology_import.html', {'typology': typology})


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
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        writer = csv.writer(response)
        writer.writerow(['Code', 'Category', 'Name'])
        
        # Write entries
        entries = typology.entries.all().order_by('code')
        for entry in entries:
            writer.writerow([entry.code, entry.category, entry.name])
        
        return response
    
    return render(request, 'datasets/typology_export.html', {'typology': typology})


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
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=503)


@login_required
def upload_files_view(request):
    """Upload files for a geometry"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'}, status=405)
    
    try:
        geometry_id = request.POST.get('geometry_id')
        files = request.FILES.getlist('files')
        
        if not geometry_id:
            return JsonResponse({'success': False, 'error': 'Geometry ID is required'}, status=400)
        
        if not files:
            return JsonResponse({'success': False, 'error': 'No files provided'}, status=400)
        
        # Validate that all files are images
        for file in files:
            if not file.content_type.startswith('image/'):
                return JsonResponse({'success': False, 'error': 'Only image files are allowed'}, status=400)
        
        # Get the geometry
        geometry = get_object_or_404(DataGeometry, pk=geometry_id)
        
        # Check if user has access to this dataset
        if not geometry.dataset.can_access(request.user):
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        uploaded_files = []
        for file in files:
            # Create DataEntryFile instance
            data_entry_file = DataEntryFile.objects.create(
                file=file,
                original_name=file.name,
                file_size=file.size,
                file_type=file.content_type,
                description='',  # No description field
                uploaded_by=request.user,
                geometry=geometry
            )
            
            uploaded_files.append({
                'id': data_entry_file.id,
                'original_name': data_entry_file.original_name,
                'file_size': data_entry_file.file_size,
                'file_type': data_entry_file.file_type,
                'description': data_entry_file.description,
                'uploaded_at': data_entry_file.uploaded_at.isoformat(),
                'download_url': data_entry_file.file.url
            })
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully uploaded {len(uploaded_files)} file(s)',
            'files': uploaded_files
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def geometry_files_view(request, geometry_id):
    """Get files for a specific geometry"""
    try:
        geometry = get_object_or_404(DataGeometry, pk=geometry_id)
        
        # Check if user has access to this dataset
        if not geometry.dataset.can_access(request.user):
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        files = DataEntryFile.objects.filter(entry__geometry=geometry).order_by('-upload_date')
        
        files_data = []
        for file in files:
            files_data.append({
                'id': file.id,
                'original_name': file.filename,
                'file_size': file.file_size,
                'file_type': file.file_type,
                'description': file.description,
                'uploaded_at': file.upload_date.isoformat(),
                'download_url': file.file.url
            })
        
        return JsonResponse({
            'success': True,
            'files': files_data
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def delete_file_view(request, file_id):
    """Delete a file"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'}, status=405)
    
    try:
        file_obj = get_object_or_404(DataEntryFile, pk=file_id)
        
        # Check if user has access to this dataset
        if not file_obj.geometry.dataset.can_access(request.user):
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        # Delete the file
        file_obj.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'File deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


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
