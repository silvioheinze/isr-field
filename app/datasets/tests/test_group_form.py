from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from ..models import DataSet, DatasetFieldConfig, DataGeometry, DataEntry, DataEntryField, Typology, TypologyEntry, DatasetField
from ..views import DatasetFieldConfigForm, DatasetFieldForm, GroupForm


class GroupFormTest(TestCase):
    """Test cases for GroupForm"""
    
    def test_form_initialization(self):
        """Test form initialization"""
        form = GroupForm()
        self.assertIsNone(form.instance.pk)
        self.assertEqual(form.Meta.model, Group)
    
    def test_form_meta_model(self):
        """Test that form Meta model is correctly set"""
        form = GroupForm()
        self.assertEqual(form.Meta.model, Group)
    
    def test_form_save_with_valid_data(self):
        """Test form save functionality with valid data"""
        form_data = {
            'name': 'Test Group'
        }
        
        form = GroupForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        group = form.save()
        
        # Verify the saved data
        self.assertEqual(group.name, 'Test Group')
        self.assertTrue(Group.objects.filter(name='Test Group').exists())
    
    def test_form_save_without_commit(self):
        """Test form save with commit=False"""
        form_data = {
            'name': 'Test Group'
        }
        
        form = GroupForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        group = form.save(commit=False)
        
        # Verify the instance is updated but not saved to database
        self.assertEqual(group.name, 'Test Group')
        
        # Verify it's not saved to database yet
        self.assertFalse(Group.objects.filter(name='Test Group').exists())
    
    def test_form_validation_empty_name(self):
        """Test form validation with empty name"""
        form_data = {
            'name': ''
        }
        
        form = GroupForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_form_validation_whitespace_name(self):
        """Test form validation with whitespace-only name"""
        form_data = {
            'name': '   '
        }
        
        form = GroupForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_form_validation_valid_data(self):
        """Test form validation with valid data"""
        form_data = {
            'name': 'Test Group'
        }
        
        form = GroupForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.errors), 0)

