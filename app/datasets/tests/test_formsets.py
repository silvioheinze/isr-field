from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from ..models import DataSet, DatasetFieldConfig, DataGeometry, DataEntry, DataEntryField, Typology, TypologyEntry, DatasetField
from ..views import DatasetFieldConfigForm, DatasetFieldForm, GroupForm


class DatasetFieldInlineFormSetTest(TestCase):
    """Comprehensive tests for DatasetFieldInlineFormSet"""
    
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
    
    def test_formset_initialization(self):
        """Test formset initialization"""
        from ..views import DatasetFieldInlineFormSet
        
        formset = DatasetFieldInlineFormSet()
        self.assertIsNotNone(formset)
        self.assertEqual(len(formset.forms), 1)  # Default number of forms
    
    def test_formset_validation_valid_data(self):
        """Test formset validation with valid data"""
        from ..views import DatasetFieldInlineFormSet
        
        form_data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-field_name': 'field1',
            'form-0-label': 'Field 1',
            'form-0-field_type': 'text',
            'form-0-required': 'on',
            'form-0-enabled': 'on',
            'form-0-order': '1',
            'form-1-field_name': 'field2',
            'form-1-label': 'Field 2',
            'form-1-field_type': 'integer',
            'form-1-required': '',
            'form-1-enabled': 'on',
            'form-1-order': '2',
        }
        
        formset = DatasetFieldInlineFormSet(data=form_data)
        self.assertTrue(formset.is_valid())
        self.assertEqual(len(formset.errors), 0)
    
    def test_formset_validation_duplicate_names(self):
        """Test formset validation with duplicate field names"""
        from ..views import DatasetFieldInlineFormSet
        
        form_data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-field_name': 'field1',
            'form-0-label': 'Field 1',
            'form-0-field_type': 'text',
            'form-0-required': 'on',
            'form-0-enabled': 'on',
            'form-0-order': '1',
            'form-1-field_name': 'field1',  # Duplicate name
            'form-1-label': 'Field 2',
            'form-1-field_type': 'integer',
            'form-1-required': '',
            'form-1-enabled': 'on',
            'form-1-order': '2',
        }
        
        formset = DatasetFieldInlineFormSet(data=form_data)
        self.assertTrue(formset.is_valid())
        # The formset should handle duplicate names at the formset level
        self.assertEqual(len(formset.errors), 0)
    
    def test_formset_validation_empty_forms(self):
        """Test formset validation with empty forms"""
        from ..views import DatasetFieldInlineFormSet
        
        form_data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-field_name': 'field1',
            'form-0-label': 'Field 1',
            'form-0-field_type': 'text',
            'form-0-required': 'on',
            'form-0-enabled': 'on',
            'form-0-order': '1',
            'form-1-field_name': '',  # Empty form
            'form-1-label': '',
            'form-1-field_type': 'text',
            'form-1-required': '',
            'form-1-enabled': '',
            'form-1-order': '',
        }
        
        formset = DatasetFieldInlineFormSet(data=form_data)
        self.assertTrue(formset.is_valid())
        # Empty forms should be ignored
        self.assertEqual(len(formset.errors), 0)
    
    def test_formset_validation_choice_fields_without_choices(self):
        """Test formset validation with choice fields without choices"""
        from ..views import DatasetFieldInlineFormSet
        
        form_data = {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-field_name': 'choice_field',
            'form-0-label': 'Choice Field',
            'form-0-field_type': 'choice',
            'form-0-required': 'on',
            'form-0-enabled': 'on',
            'form-0-choices': '',  # No choices provided
            'form-0-order': '1',
        }
        
        formset = DatasetFieldInlineFormSet(data=form_data)
        self.assertFalse(formset.is_valid())
        # The form should report missing choices error
        self.assertIn('Provide manual choices or select a typology for choice fields.', formset.forms[0].errors.get('choices', []))
    
    def test_formset_save_with_valid_data(self):
        """Test formset save functionality with valid data"""
        from ..views import DatasetFieldInlineFormSet
        
        form_data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-field_name': 'field1',
            'form-0-label': 'Field 1',
            'form-0-field_type': 'text',
            'form-0-required': 'on',
            'form-0-enabled': 'on',
            'form-0-order': '1',
            'form-1-field_name': 'field2',
            'form-1-label': 'Field 2',
            'form-1-field_type': 'integer',
            'form-1-required': '',
            'form-1-enabled': 'on',
            'form-1-order': '2',
        }
        
        formset = DatasetFieldInlineFormSet(data=form_data)
        self.assertTrue(formset.is_valid())
        
        # Save the formset
        instances = formset.save(commit=False)
        for instance in instances:
            instance.dataset = self.dataset
            instance.save()
        
        # Verify the fields were created
        self.assertTrue(DatasetField.objects.filter(dataset=self.dataset, field_name='field1').exists())
        self.assertTrue(DatasetField.objects.filter(dataset=self.dataset, field_name='field2').exists())
