from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from ..models import DataSet, DatasetFieldConfig, DataGeometry, DataEntry, DataEntryField, Typology, TypologyEntry, DatasetField
from ..views import DatasetFieldConfigForm, DatasetFieldForm, GroupForm


class DatasetFieldFormTest(TestCase):
    """Test cases for DatasetFieldForm"""
    
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
    
    def test_form_initialization_without_instance(self):
        """Test form initialization without model instance"""
        form = DatasetFieldForm()
        self.assertIsNone(form.instance.pk)
        self.assertEqual(form.Meta.model, DatasetField)
    
    def test_form_initialization_with_instance(self):
        """Test form initialization with model instance"""
        custom_field = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='test_field',
            label='Test Field',
            field_type='text',
            required=True,
            enabled=True,
            help_text='Test help text',
            order=1
        )
        
        form = DatasetFieldForm(instance=custom_field)
        self.assertEqual(form.instance, custom_field)
        self.assertEqual(form.initial['field_name'], 'test_field')
        self.assertEqual(form.initial['label'], 'Test Field')
        self.assertEqual(form.initial['field_type'], 'text')
        self.assertEqual(form.initial['required'], True)
        self.assertEqual(form.initial['enabled'], True)
        self.assertEqual(form.initial['help_text'], 'Test help text')
        self.assertEqual(form.initial['order'], 1)
    
    def test_form_validation_valid_text_field(self):
        """Test form validation with valid text field data"""
        form_data = {
            'field_name': 'test_field',
            'label': 'Test Field',
            'field_type': 'text',
            'required': True,
            'enabled': True,
            'help_text': 'This is a test field',
            'order': 1
        }
        
        form = DatasetFieldForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.errors), 0)
    
    def test_form_validation_valid_integer_field(self):
        """Test form validation with valid integer field data"""
        form_data = {
            'field_name': 'count_field',
            'label': 'Count Field',
            'field_type': 'integer',
            'required': True,
            'enabled': True,
            'help_text': 'Enter a number',
            'order': 2
        }
        
        form = DatasetFieldForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.errors), 0)
    
    def test_form_validation_valid_decimal_field(self):
        """Test form validation with valid decimal field data"""
        form_data = {
            'field_name': 'price_field',
            'label': 'Price Field',
            'field_type': 'decimal',
            'required': True,
            'enabled': True,
            'help_text': 'Enter a price',
            'order': 3
        }
        
        form = DatasetFieldForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.errors), 0)
    
    def test_form_validation_valid_boolean_field(self):
        """Test form validation with valid boolean field data"""
        form_data = {
            'field_name': 'active_field',
            'label': 'Active Field',
            'field_type': 'boolean',
            'required': False,
            'enabled': True,
            'help_text': 'Check if active',
            'order': 4
        }
        
        form = DatasetFieldForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.errors), 0)
    
    def test_form_validation_valid_date_field(self):
        """Test form validation with valid date field data"""
        form_data = {
            'field_name': 'created_date',
            'label': 'Created Date',
            'field_type': 'date',
            'required': True,
            'enabled': True,
            'help_text': 'Enter a date',
            'order': 5
        }
        
        form = DatasetFieldForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.errors), 0)
    
    def test_form_validation_choice_field_with_choices(self):
        """Test form validation for choice field with choices"""
        form_data = {
            'field_name': 'status_field',
            'label': 'Status Field',
            'field_type': 'choice',
            'required': True,
            'enabled': True,
            'choices': 'Active, Inactive, Pending',
            'order': 6
        }
        
        form = DatasetFieldForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(len(form.errors), 0)
    
    def test_form_validation_choice_field_without_choices(self):
        """Test form validation for choice field without choices"""
        form_data = {
            'field_name': 'status_field',
            'label': 'Status Field',
            'field_type': 'choice',
            'required': True,
            'enabled': True,
            'choices': '',  # No choices provided
            'order': 6
        }
        
        form = DatasetFieldForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('choices', form.errors)
    
    def test_form_validation_choice_field_with_whitespace_choices(self):
        """Test form validation for choice field with whitespace-only choices"""
        form_data = {
            'field_name': 'status_field',
            'label': 'Status Field',
            'field_type': 'choice',
            'required': True,
            'enabled': True,
            'choices': '   ,   ,   ',  # Whitespace only
            'order': 6
        }
        
        form = DatasetFieldForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('choices', form.errors)
    
    def test_form_typology_category_choices_population(self):
        """Typology categories should populate when a typology is selected"""
        typology = Typology.objects.create(name='Usage Typology', created_by=self.user)
        TypologyEntry.objects.create(typology=typology, code=1, category='Residential', name='Single Family')
        TypologyEntry.objects.create(typology=typology, code=2, category='Commercial', name='Retail')

        form = DatasetFieldForm()
        # Ensure initial choices contain default option only when no typology selected
        self.assertEqual(form.fields['typology_category'].choices, [('', 'All categories')])

        form_with_typology = DatasetFieldForm(data={
            'field_name': 'usage',
            'label': 'Usage',
            'field_type': 'choice',
            'required': True,
            'enabled': True,
            'order': 1,
            'typology': str(typology.id)
        })
        # Trigger validation to populate cleaned data
        form_with_typology.is_valid()
        choices = form_with_typology.fields['typology_category'].choices
        self.assertIn(('Residential', 'Residential'), choices)
        self.assertIn(('Commercial', 'Commercial'), choices)
    
    def test_form_validation_missing_required_fields(self):
        """Test form validation with missing required fields"""
        form_data = {
            'field_name': '',  # Missing field_name
            'label': '',  # Missing label
            'field_type': 'text'
        }
        
        form = DatasetFieldForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('field_name', form.errors)
        self.assertIn('label', form.errors)
    
    def test_form_save_with_valid_data(self):
        """Test form save functionality with valid data"""
        form_data = {
            'field_name': 'test_field_name',
            'label': 'Test Field',
            'field_type': 'text',
            'required': True,
            'enabled': True,
            'help_text': 'Test help text',
            'order': 1
        }
        
        form = DatasetFieldForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        custom_field = form.save(commit=False)
        custom_field.dataset = self.dataset
        custom_field.save()
        
        # Verify the saved data
        self.assertEqual(custom_field.field_name, 'test_field_name')
        self.assertEqual(custom_field.label, 'Test Field')
        self.assertEqual(custom_field.field_type, 'text')
        self.assertTrue(custom_field.required)
        self.assertTrue(custom_field.enabled)
        self.assertEqual(custom_field.help_text, 'Test help text')
        self.assertEqual(custom_field.order, 1)
        self.assertEqual(custom_field.dataset, self.dataset)
    
    def test_form_save_without_commit(self):
        """Test form save with commit=False"""
        form_data = {
            'field_name': 'test_field_name',
            'label': 'Test Field',
            'field_type': 'text',
            'required': True,
            'enabled': True,
            'help_text': 'Test help text',
            'order': 1
        }
        
        form = DatasetFieldForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        custom_field = form.save(commit=False)
        custom_field.dataset = self.dataset
        
        # Verify the instance is updated but not saved to database
        self.assertEqual(custom_field.field_name, 'test_field_name')
        self.assertEqual(custom_field.label, 'Test Field')
        self.assertEqual(custom_field.field_type, 'text')
        
        # Verify it's not saved to database yet
        self.assertFalse(DatasetField.objects.filter(field_name='test_field_name').exists())
    
    def test_form_widget_attributes(self):
        """Test that form widgets have correct attributes"""
        form = DatasetFieldForm()
        
        # Check text input widgets
        self.assertIn('form-control', str(form['field_name'].field.widget.attrs['class']))
        self.assertIn('form-control', str(form['label'].field.widget.attrs['class']))
        self.assertIn('form-control', str(form['help_text'].field.widget.attrs['class']))
        
        # Check select widgets
        self.assertIn('form-select', str(form['field_type'].field.widget.attrs['class']))
        
        # Check checkbox widgets
        self.assertIn('form-check-input', str(form['required'].field.widget.attrs['class']))
        self.assertIn('form-check-input', str(form['enabled'].field.widget.attrs['class']))
        
        # Check number input widgets
        self.assertIn('form-control', str(form['order'].field.widget.attrs['class']))
        self.assertEqual(form['order'].field.widget.attrs['min'], '-1')  # Allow -1 for "last" position

