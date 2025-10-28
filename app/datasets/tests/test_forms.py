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
        self.assertEqual(form['order'].field.widget.attrs['min'], 0)


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
