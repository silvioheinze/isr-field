from django.contrib.auth.forms import UserCreationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth import login as auth_login, logout
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserChangeForm, PasswordChangeForm
from django.contrib import messages
from django.urls import reverse
from django import forms
from django.contrib.auth import update_session_auth_hash
from django.http import HttpResponse, JsonResponse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail
from datetime import datetime

from ..models import AuditLog, DataSet


def health_check_view(request):
    """Health check endpoint for monitoring"""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


def password_reset_view(request):
    """Password reset request view"""
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                # Generate password reset token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Create reset URL
                current_site = get_current_site(request)
                reset_url = f"http://{current_site.domain}/reset-password/{uid}/{token}/"
                
                # Send email
                subject = 'Password Reset Request'
                message = f"""
                You requested a password reset for your account.
                
                Please click the following link to reset your password:
                {reset_url}
                
                If you did not request this, please ignore this email.
                """
                
                send_mail(subject, message, 'noreply@example.com', [email])
                messages.success(request, 'Password reset email sent!')
                return redirect('password_reset_done')
            except User.DoesNotExist:
                messages.error(request, 'No account found with that email address.')
    else:
        form = PasswordResetForm()
    
    return render(request, 'datasets/password_reset.html', {'form': form})


def password_reset_done_view(request):
    """Password reset done view"""
    return render(request, 'datasets/password_reset_done.html')


def password_reset_confirm_view(request, uidb64, token):
    """Password reset confirmation view"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your password has been reset successfully!')
                return redirect('login')
        else:
            form = SetPasswordForm(user)
        
        return render(request, 'datasets/password_reset_confirm.html', {'form': form})
    else:
        messages.error(request, 'Invalid password reset link.')
        return redirect('password_reset')


def password_reset_complete_view(request):
    """Password reset complete view"""
    return render(request, 'datasets/password_reset_complete.html')


@login_required
def dashboard_view(request):
    """Main dashboard view"""
    # Get datasets owned by user or shared with user
    owned_datasets = DataSet.objects.filter(owner=request.user)
    shared_datasets = DataSet.objects.filter(shared_with=request.user)
    group_shared_datasets = DataSet.objects.filter(shared_with_groups__in=request.user.groups.all())
    public_datasets = DataSet.objects.filter(is_public=True)
    
    # Combine and deduplicate
    all_datasets = (owned_datasets | shared_datasets | group_shared_datasets | public_datasets).distinct()
    
    return render(request, 'datasets/dashboard.html', {
        'datasets': all_datasets
    })


def register_view(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    
    return render(request, 'datasets/register.html', {'form': form})


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully!')
    return redirect('login')


@login_required
def profile_view(request):
    """User profile view"""
    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserChangeForm(instance=request.user)
    
    return render(request, 'datasets/profile.html', {'form': form})


def is_manager(user):
    """Check if user is a manager"""
    return user.groups.filter(name='Managers').exists()


@login_required
@permission_required('auth.add_user')
def user_management_view(request):
    """User management view"""
    users = User.objects.all()
    return render(request, 'datasets/user_management.html', {'users': users})


@login_required
@permission_required('auth.change_user')
def edit_user_view(request, user_id):
    """Edit user view"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User {user.username} updated successfully!')
            return redirect('user_management')
    else:
        form = UserChangeForm(instance=user)
    
    return render(request, 'datasets/edit_user.html', {
        'form': form,
        'user': user
    })


@login_required
@permission_required('auth.delete_user')
def delete_user_view(request, user_id):
    """Delete user view"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User {username} deleted successfully!')
        return redirect('user_management')
    
    return render(request, 'datasets/delete_user.html', {'user': user})


@login_required
@permission_required('auth.add_user')
def create_user_view(request):
    """Create user view"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User {user.username} created successfully!')
            return redirect('user_management')
    else:
        form = UserCreationForm()
    
    return render(request, 'datasets/create_user.html', {'form': form})


@login_required
@permission_required('auth.add_group')
def create_group_view(request):
    """Create group view"""
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            group = Group.objects.create(name=name)
            messages.success(request, f'Group {name} created successfully!')
            return redirect('user_management')
        else:
            messages.error(request, 'Group name is required.')
    
    return render(request, 'datasets/create_group.html')


@login_required
@permission_required('auth.change_user')
def modify_user_groups_view(request, user_id):
    """Modify user groups view"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        group_ids = request.POST.getlist('groups')
        user.groups.set(Group.objects.filter(id__in=group_ids))
        messages.success(request, f'Groups updated for {user.username}!')
        return redirect('user_management')
    
    return render(request, 'datasets/modify_user_groups.html', {
        'user': user,
        'groups': Group.objects.all()
    })


@login_required
@permission_required('auth.change_group')
def edit_group_view(request, group_id):
    """Edit group view"""
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            group.name = name
            group.save()
            messages.success(request, f'Group {name} updated successfully!')
            return redirect('user_management')
        else:
            messages.error(request, 'Group name is required.')
    
    return render(request, 'datasets/edit_group.html', {'group': group})
