from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from ..models import DataSet, DatasetFieldConfig, DataGeometry, DataEntry, DataEntryField, Typology, TypologyEntry, DatasetField
from ..views import DatasetFieldConfigForm, DatasetFieldForm, GroupForm


class DatasetFieldConfigFormTest(TestCase):
    """Test cases for DatasetFieldConfigForm"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.dataset = DataSet.objects.create(
            name='Test Dataset',
            description='Test Description',
            owner=self.user
        )
        self.config = DatasetFieldConfig.objects.create(dataset=self.dataset)
    
    def test_form_initialization_without_instance(self):
        """Test form initialization without model instance"""
        form = DatasetFieldConfigForm()
        self.assertIsNone(form.instance.pk)
        self.assertEqual(form.Meta.model, DatasetFieldConfig)
    
    def test_form_initialization_with_instance(self):
        """Test form initialization with model instance"""
        form = DatasetFieldConfigForm(instance=self.config)
        self.assertEqual(form.instance, self.config)
        self.assertEqual(form.initial['usage_code1_label'], 'Usage Code 1')
        self.assertEqual(form.initial['usage_code1_enabled'], True)
    
    def test_form_validation_valid_data(self):
        """Test form validation with valid data"""
        form_data = {
            'usage_code1_label': 'Custom Usage 1',
            'usage_code1_enabled': True,
            'usage_code2_label': 'Custom Usage 2',
            'usage_code2_enabled': False,
            'usage_code3_label': 'Custom Usage 3',
            'usage_code3_enabled': True,
            'cat_inno_label': 'Custom Innovation',
            'cat_inno_enabled': True,
            'cat_wert_label': 'Custom Value',
            'cat_wert_enabled': True,
            'cat_fili_label': 'Custom Facility',
            'cat_fili_enabled': True,
            'year_label': 'Custom Year',
            'year_enabled': True,
            'name_label': 'Custom Name',
            'name_enabled': True
        }
        
        form = DatasetFieldConfigForm(data=form_data, instance=self.config)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.errors), 0)
    
    def test_form_validation_empty_labels(self):
        """Test form validation with empty labels"""
        form_data = {
            'usage_code1_label': '',  # Empty label should be invalid
            'usage_code1_enabled': 'invalid_boolean',  # Invalid boolean
        }
        
        form = DatasetFieldConfigForm(data=form_data, instance=self.config)
        self.assertFalse(form.is_valid())
        self.assertIn('usage_code1_label', form.errors)
    
    def test_form_save_with_valid_data(self):
        """Test form save functionality with valid data"""
        form_data = {
            'usage_code1_label': 'Updated Usage 1',
            'usage_code1_enabled': False,
            'usage_code2_label': 'Updated Usage 2',
            'usage_code2_enabled': True,
            'usage_code3_label': 'Updated Usage 3',
            'usage_code3_enabled': True,
            'cat_inno_label': 'Updated Innovation',
            'cat_inno_enabled': True,
            'cat_wert_label': 'Updated Value',
            'cat_wert_enabled': True,
            'cat_fili_label': 'Updated Facility',
            'cat_fili_enabled': True,
            'year_label': 'Updated Year',
            'year_enabled': True,
            'name_label': 'Updated Name',
            'name_enabled': True
        }
        
        form = DatasetFieldConfigForm(data=form_data, instance=self.config)
        self.assertTrue(form.is_valid())
        
        saved_config = form.save()
        
        # Verify the saved data
        self.assertEqual(saved_config.usage_code1_label, 'Updated Usage 1')
        self.assertFalse(saved_config.usage_code1_enabled)
        self.assertEqual(saved_config.usage_code2_label, 'Updated Usage 2')
        self.assertTrue(saved_config.usage_code2_enabled)
        self.assertEqual(saved_config.cat_inno_label, 'Updated Innovation')
        self.assertTrue(saved_config.cat_inno_enabled)
        self.assertEqual(saved_config.year_label, 'Updated Year')
        self.assertTrue(saved_config.year_enabled)
        self.assertEqual(saved_config.name_label, 'Updated Name')
        self.assertTrue(saved_config.name_enabled)
    
    def test_form_save_without_commit(self):
        """Test form save with commit=False"""
        form_data = {
            'usage_code1_label': 'Updated Usage 1',
            'usage_code1_enabled': False,
            'usage_code2_label': 'Updated Usage 2',
            'usage_code2_enabled': True,
            'usage_code3_label': 'Updated Usage 3',
            'usage_code3_enabled': True,
            'cat_inno_label': 'Updated Innovation',
            'cat_inno_enabled': True,
            'cat_wert_label': 'Updated Value',
            'cat_wert_enabled': True,
            'cat_fili_label': 'Updated Facility',
            'cat_fili_enabled': True,
            'year_label': 'Updated Year',
            'year_enabled': True,
            'name_label': 'Updated Name',
            'name_enabled': True
        }
        
        form = DatasetFieldConfigForm(data=form_data, instance=self.config)
        self.assertTrue(form.is_valid())
        
        saved_config = form.save(commit=False)
        
        # Verify the instance is updated but not saved to database
        self.assertEqual(saved_config.usage_code1_label, 'Updated Usage 1')
        self.assertFalse(saved_config.usage_code1_enabled)
        
        # Verify it's not saved to database yet
        self.config.refresh_from_db()
        self.assertEqual(self.config.usage_code1_label, 'Usage Code 1')  # Original value
    
    def test_form_widget_attributes(self):
        """Test that form widgets have correct attributes"""
        form = DatasetFieldConfigForm()
        
        # Check text input widgets
        self.assertIn('form-control', str(form['usage_code1_label'].field.widget.attrs['class']))
        self.assertIn('form-control', str(form['usage_code2_label'].field.widget.attrs['class']))
        self.assertIn('form-control', str(form['cat_inno_label'].field.widget.attrs['class']))
        
        # Check checkbox widgets
        self.assertIn('form-check-input', str(form['usage_code1_enabled'].field.widget.attrs['class']))
        self.assertIn('form-check-input', str(form['usage_code2_enabled'].field.widget.attrs['class']))
        self.assertIn('form-check-input', str(form['cat_inno_enabled'].field.widget.attrs['class']))

