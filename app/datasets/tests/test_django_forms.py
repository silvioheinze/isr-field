from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from ..models import DataSet, DatasetFieldConfig, DataGeometry, DataEntry, DataEntryField, Typology, TypologyEntry, DatasetField
from ..views import DatasetFieldConfigForm, DatasetFieldForm, GroupForm


class DjangoBuiltInFormsTest(TestCase):
    """Test cases for Django built-in forms used in the application"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_user_creation_form_valid_data(self):
        """Test UserCreationForm with valid data"""
        form_data = {
            'username': 'newuser',
            'password1': 'newpass123',
            'password2': 'newpass123',
        }
        
        form = UserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.errors), 0)
    
    def test_user_creation_form_password_mismatch(self):
        """Test UserCreationForm with password mismatch"""
        form_data = {
            'username': 'newuser',
            'password1': 'newpass123',
            'password2': 'differentpass123',
        }
        
        form = UserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
    
    def test_user_creation_form_duplicate_username(self):
        """Test UserCreationForm with duplicate username"""
        form_data = {
            'username': 'testuser',  # Already exists
            'password1': 'newpass123',
            'password2': 'newpass123',
        }
        
        form = UserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
    
    def test_password_change_form_valid_data(self):
        """Test PasswordChangeForm with valid data"""
        form_data = {
            'old_password': 'testpass123',
            'new_password1': 'newpass123',
            'new_password2': 'newpass123',
        }
        
        form = PasswordChangeForm(user=self.user, data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.errors), 0)
    
    def test_password_change_form_wrong_old_password(self):
        """Test PasswordChangeForm with wrong old password"""
        form_data = {
            'old_password': 'wrongpass123',
            'new_password1': 'newpass123',
            'new_password2': 'newpass123',
        }
        
        form = PasswordChangeForm(user=self.user, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('old_password', form.errors)
    
    def test_password_change_form_password_mismatch(self):
        """Test PasswordChangeForm with password mismatch"""
        form_data = {
            'old_password': 'testpass123',
            'new_password1': 'newpass123',
            'new_password2': 'differentpass123',
        }
        
        form = PasswordChangeForm(user=self.user, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('new_password2', form.errors)
    
    def test_password_reset_form_valid_data(self):
        """Test PasswordResetForm with valid data"""
        form_data = {
            'email': 'test@example.com',
        }
        
        form = PasswordResetForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.errors), 0)
    
    def test_password_reset_form_invalid_email(self):
        """Test PasswordResetForm with invalid email"""
        form_data = {
            'email': 'invalid-email',
        }
        
        form = PasswordResetForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_set_password_form_valid_data(self):
        """Test SetPasswordForm with valid data"""
        form_data = {
            'new_password1': 'newpass123',
            'new_password2': 'newpass123',
        }
        
        form = SetPasswordForm(user=self.user, data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.errors), 0)
    
    def test_set_password_form_password_mismatch(self):
        """Test SetPasswordForm with password mismatch"""
        form_data = {
            'new_password1': 'newpass123',
            'new_password2': 'differentpass123',
        }
        
        form = SetPasswordForm(user=self.user, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('new_password2', form.errors)
