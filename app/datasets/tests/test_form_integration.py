from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from ..models import DataSet, DatasetFieldConfig, DataGeometry, DataEntry, DataEntryField, Typology, TypologyEntry, DatasetField
from ..views import DatasetFieldConfigForm, DatasetFieldForm, GroupForm


class FormIntegrationTest(TestCase):
    """Integration tests for forms working together"""
    
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
    
    def test_form_initial_values(self):
        """Test form initial values"""
        # Test DatasetFieldConfigForm initial values
        config_form = DatasetFieldConfigForm(instance=self.config)
        self.assertEqual(config_form.initial['usage_code1_label'], 'Usage Code 1')
        self.assertTrue(config_form.initial['usage_code1_enabled'])
        
        # Test DatasetFieldForm initial values
        field_form = DatasetFieldForm()
        self.assertIsNone(field_form.initial.get('field_name'))
        
        # Test GroupForm initial values
        group_form = GroupForm()
        self.assertIsNone(group_form.initial.get('name'))
    
    def test_form_validation_error_handling(self):
        """Test comprehensive form validation error handling"""
        # Test DatasetFieldConfigForm with invalid data
        invalid_config_data = {
            'usage_code1_label': '',  # Empty label
            'usage_code1_enabled': 'invalid_boolean',
        }
        config_form = DatasetFieldConfigForm(data=invalid_config_data, instance=self.config)
        self.assertFalse(config_form.is_valid())
        self.assertIn('usage_code1_label', config_form.errors)
        
        # Test DatasetFieldForm with invalid data
        invalid_field_data = {
            'field_name': '',  # Empty field name
            'label': '',  # Empty label
            'field_type': 'choice',
            'choices': '',  # No choices for choice field
        }
        field_form = DatasetFieldForm(data=invalid_field_data)
        self.assertFalse(field_form.is_valid())
        self.assertIn('field_name', field_form.errors)
        self.assertIn('label', field_form.errors)
        self.assertIn('choices', field_form.errors)
        
        # Test GroupForm with invalid data
        invalid_group_data = {
            'name': '',  # Empty name
        }
        group_form = GroupForm(data=invalid_group_data)
        self.assertFalse(group_form.is_valid())
        self.assertIn('name', group_form.errors)
    
    def test_form_widget_rendering(self):
        """Test that form widgets render correctly"""
        # Test DatasetFieldConfigForm widgets
        config_form = DatasetFieldConfigForm()
        self.assertIn('form-control', str(config_form['usage_code1_label'].field.widget.attrs['class']))
        self.assertIn('form-check-input', str(config_form['usage_code1_enabled'].field.widget.attrs['class']))
        
        # Test DatasetFieldForm widgets
        field_form = DatasetFieldForm()
        self.assertIn('form-control', str(field_form['field_name'].field.widget.attrs['class']))
        self.assertIn('form-select', str(field_form['field_type'].field.widget.attrs['class']))
        self.assertIn('form-check-input', str(field_form['required'].field.widget.attrs['class']))
        
        # Test GroupForm widgets
        group_form = GroupForm()
        self.assertIn('form-control', str(group_form['name'].field.widget.attrs['class']))
    
    def test_custom_field_form_with_dataset_context(self):
        """Test DatasetFieldForm with dataset context"""
        form_data = {
            'field_name': 'test_field',
            'label': 'Test Field',
            'field_type': 'text',
            'required': True,
            'enabled': True,
            'help_text': 'Test help text',
            'order': 1
        }
        
        form = DatasetFieldForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Save with dataset context
        field = form.save(commit=False)
        field.dataset = self.dataset
        field.save()
        
        # Verify the field was created with correct dataset
        self.assertEqual(field.dataset, self.dataset)
        self.assertTrue(DatasetField.objects.filter(dataset=self.dataset, field_name='test_field').exists())
    
    def test_dataset_field_config_form_with_custom_fields(self):
        """Test DatasetFieldConfigForm with custom fields"""
        # Create some custom fields
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='custom_field_1',
            label='Custom Field 1',
            field_type='text',
            enabled=True,
            order=1
        )
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='custom_field_2',
            label='Custom Field 2',
            field_type='integer',
            enabled=False,
            order=2
        )
        
        # Test form with custom fields
        form = DatasetFieldConfigForm(instance=self.config)
        self.assertEqual(form.instance, self.config)
        self.assertEqual(form.initial['usage_code1_label'], 'Usage Code 1')
        self.assertTrue(form.initial['usage_code1_enabled'])
    
    def test_form_clean_methods_integration(self):
        """Test integration of form clean methods"""
        # Test DatasetFieldForm clean_field_name method
        form_data = {
            'field_name': 'Test Field Name!@#',
            'label': 'Test Field',
            'field_type': 'text',
            'required': True,
            'enabled': True,
            'order': 1
        }
        
        form = DatasetFieldForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # The clean_field_name method should clean the field name
        cleaned_field_name = form.cleaned_data['field_name']
        self.assertEqual(cleaned_field_name, 'test_field_name')
    
    def test_formset_with_mixed_valid_invalid_forms(self):
        """Test formset with mix of valid and invalid forms"""
        from ..views import DatasetFieldInlineFormSet
        
        form_data = {
            'form-TOTAL_FORMS': '2',
            'form-INITIAL_FORMS': '0',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-field_name': 'valid_field',
            'form-0-label': 'Valid Field',
            'form-0-field_type': 'text',
            'form-0-required': 'on',
            'form-0-enabled': 'on',
            'form-0-order': '1',
            'form-1-field_name': '',  # Invalid form
            'form-1-label': '',
            'form-1-field_type': 'text',
            'form-1-required': '',
            'form-1-enabled': '',
            'form-1-order': '',
        }
        
        formset = DatasetFieldInlineFormSet(data=form_data)
        self.assertTrue(formset.is_valid())
        # The formset should handle mixed valid/invalid forms correctly
        self.assertEqual(len(formset.errors), 0)
