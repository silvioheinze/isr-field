from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from .models import DataSet, DatasetFieldConfig, DataGeometry, DataEntry, Typology, TypologyEntry, CustomField
from .views import DatasetFieldConfigForm
from django.contrib.gis.geos import Point


class DatasetFieldConfigModelTest(TestCase):
    """Test cases for DatasetFieldConfig model"""
    
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
    
    def test_dataset_field_config_creation(self):
        """Test creating a DatasetFieldConfig"""
        config = DatasetFieldConfig.objects.create(dataset=self.dataset)
        
        self.assertEqual(config.dataset, self.dataset)
        self.assertEqual(config.usage_code1_label, 'Usage Code 1')
        self.assertEqual(config.usage_code2_label, 'Usage Code 2')
        self.assertEqual(config.usage_code3_label, 'Usage Code 3')
        self.assertEqual(config.cat_inno_label, 'Category Innovation')
        self.assertEqual(config.cat_wert_label, 'Category Value')
        self.assertEqual(config.cat_fili_label, 'Category Filial')
        self.assertEqual(config.year_label, 'Year')
        self.assertEqual(config.name_label, 'Entry Name')
        
        # Test default enabled states
        self.assertTrue(config.usage_code1_enabled)
        self.assertTrue(config.usage_code2_enabled)
        self.assertTrue(config.usage_code3_enabled)
        self.assertTrue(config.cat_inno_enabled)
        self.assertTrue(config.cat_wert_enabled)
        self.assertTrue(config.cat_fili_enabled)
        self.assertTrue(config.year_enabled)
        self.assertTrue(config.name_enabled)
    
    def test_dataset_field_config_str(self):
        """Test string representation of DatasetFieldConfig"""
        config = DatasetFieldConfig.objects.create(dataset=self.dataset)
        expected_str = f"Field Config for {self.dataset.name}"
        self.assertEqual(str(config), expected_str)
    
    def test_dataset_field_config_one_to_one_relationship(self):
        """Test that each dataset can only have one field config"""
        # Create first config
        config1 = DatasetFieldConfig.objects.create(dataset=self.dataset)
        
        # Try to create second config for same dataset - should raise IntegrityError
        with self.assertRaises(IntegrityError):
            DatasetFieldConfig.objects.create(dataset=self.dataset)
    
    def test_dataset_field_config_cascade_delete(self):
        """Test that field config is deleted when dataset is deleted"""
        config = DatasetFieldConfig.objects.create(dataset=self.dataset)
        config_id = config.id
        
        # Delete the dataset
        self.dataset.delete()
        
        # Check that the field config is also deleted
        self.assertFalse(DatasetFieldConfig.objects.filter(id=config_id).exists())
    
    def test_dataset_field_config_custom_values(self):
        """Test setting custom values for field config"""
        config = DatasetFieldConfig.objects.create(
            dataset=self.dataset,
            usage_code1_label='Custom Usage 1',
            usage_code1_enabled=False,
            cat_inno_label='Custom Innovation',
            cat_inno_enabled=False,
            year_label='Custom Year',
            year_enabled=False
        )
        
        self.assertEqual(config.usage_code1_label, 'Custom Usage 1')
        self.assertFalse(config.usage_code1_enabled)
        self.assertEqual(config.cat_inno_label, 'Custom Innovation')
        self.assertFalse(config.cat_inno_enabled)
        self.assertEqual(config.year_label, 'Custom Year')
        self.assertFalse(config.year_enabled)


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
    
    def test_form_initialization(self):
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
            'cat_wert_enabled': False,
            'cat_fili_label': 'Custom Filial',
            'cat_fili_enabled': True,
            'year_label': 'Custom Year',
            'year_enabled': True,
            'name_label': 'Custom Name',
            'name_enabled': False
        }
        
        form = DatasetFieldConfigForm(data=form_data, instance=self.config)
        self.assertTrue(form.is_valid())
    
    def test_form_validation_invalid_data(self):
        """Test form validation with invalid data"""
        form_data = {
            'usage_code1_label': '',  # Empty label should be invalid
            'usage_code1_enabled': 'invalid_boolean',  # Invalid boolean
        }
        
        form = DatasetFieldConfigForm(data=form_data, instance=self.config)
        self.assertFalse(form.is_valid())
    
    def test_form_save(self):
        """Test form save functionality"""
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
            'cat_fili_label': 'Updated Filial',
            'cat_fili_enabled': True,
            'year_label': 'Updated Year',
            'year_enabled': True,
            'name_label': 'Updated Name',
            'name_enabled': True
        }
        
        form = DatasetFieldConfigForm(data=form_data, instance=self.config)
        self.assertTrue(form.is_valid())
        
        saved_config = form.save()
        
        self.assertEqual(saved_config.usage_code1_label, 'Updated Usage 1')
        self.assertFalse(saved_config.usage_code1_enabled)
        self.assertEqual(saved_config.usage_code2_label, 'Updated Usage 2')
        self.assertTrue(saved_config.usage_code2_enabled)


class DatasetFieldConfigViewTest(TestCase):
    """Test cases for dataset field configuration views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        self.dataset = DataSet.objects.create(
            name='Test Dataset',
            description='Test Description',
            owner=self.user
        )
        self.config = DatasetFieldConfig.objects.create(dataset=self.dataset)
    
    def test_dataset_detail_view_includes_field_config(self):
        """Test that dataset detail view includes field configuration"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dataset_detail', args=[self.dataset.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('all_fields', response.context)
        # Check that standard fields are present
        all_fields = response.context['all_fields']
        self.assertTrue(all_fields.filter(is_standard_field=True).exists())
    
    def test_dataset_field_config_view_get(self):
        """Test GET request to field configuration view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('all_fields', response.context)
        self.assertIn('dataset', response.context)
        self.assertEqual(response.context['dataset'], self.dataset)
        # Check that standard fields are present
        all_fields = response.context['all_fields']
        self.assertTrue(all_fields.filter(is_standard_field=True).exists())
    
    def test_dataset_field_config_view_post_valid(self):
        """Test POST request with valid data to field configuration view"""
        self.client.login(username='testuser', password='testpass123')
        
        # First, access the field config page to create standard fields
        self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        
        # Get the standard fields for this dataset
        from datasets.models import CustomField
        standard_fields = CustomField.objects.filter(dataset=self.dataset, is_standard_field=True)
        
        form_data = {}
        for field in standard_fields:
            form_data[f'field_{field.id}_label'] = f'Updated {field.label}'
            form_data[f'field_{field.id}_enabled'] = 'on'
            form_data[f'field_{field.id}_required'] = 'on' if field.name == 'year' else ''
            form_data[f'field_{field.id}_help_text'] = f'Help for {field.label}'
            form_data[f'field_{field.id}_order'] = field.order
        
        response = self.client.post(reverse('dataset_field_config', args=[self.dataset.id]), form_data)
        
        # Should redirect to dataset detail
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dataset_detail', args=[self.dataset.id]))
        
        # Check that the fields were updated
        updated_fields = CustomField.objects.filter(dataset=self.dataset, is_standard_field=True)
        for field in updated_fields:
            field.refresh_from_db()
            # Check that the label starts with "Updated"
            self.assertTrue(field.label.startswith('Updated'))
            self.assertTrue(field.enabled)
    
    def test_dataset_field_config_view_unauthorized_user(self):
        """Test that unauthorized users cannot access field configuration"""
        self.client.login(username='otheruser', password='otherpass123')
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        
        self.assertEqual(response.status_code, 403)
    
    def test_dataset_field_config_view_unauthenticated(self):
        """Test that unauthenticated users cannot access field configuration"""
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_dataset_field_config_view_nonexistent_dataset(self):
        """Test field configuration view with nonexistent dataset"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dataset_field_config', args=[999]))
        
        self.assertEqual(response.status_code, 404)


class DatasetFieldConfigIntegrationTest(TestCase):
    """Integration tests for dataset field configuration feature"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
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
    
    def test_automatic_field_config_creation(self):
        """Test that standard fields are automatically created when viewing dataset"""
        from datasets.models import CustomField
        
        # Initially no standard fields should exist
        self.assertFalse(CustomField.objects.filter(dataset=self.dataset, is_standard_field=True).exists())
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dataset_detail', args=[self.dataset.id]))
        
        # After viewing dataset detail, standard fields should be created
        self.assertTrue(CustomField.objects.filter(dataset=self.dataset, is_standard_field=True).exists())
        standard_fields = CustomField.objects.filter(dataset=self.dataset, is_standard_field=True)
        
        # Check that we have the expected standard fields
        field_names = [field.name for field in standard_fields]
        expected_fields = ['name', 'usage_code1', 'usage_code2', 'usage_code3', 'cat_inno', 'cat_wert', 'cat_fili', 'year']
        for expected_field in expected_fields:
            self.assertIn(expected_field, field_names)
    
    def test_field_configuration_workflow(self):
        """Test complete workflow of configuring dataset fields"""
        from datasets.models import CustomField
        
        self.client.login(username='testuser', password='testpass123')
        
        # 1. View dataset detail (should create standard fields)
        response = self.client.get(reverse('dataset_detail', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(CustomField.objects.filter(dataset=self.dataset, is_standard_field=True).exists())
        
        # 2. Access field configuration page
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        
        # 3. Update field configuration
        standard_fields = CustomField.objects.filter(dataset=self.dataset, is_standard_field=True)
        form_data = {}
        for field in standard_fields:
            form_data[f'field_{field.id}_label'] = f'Updated {field.label}'
            form_data[f'field_{field.id}_enabled'] = 'on'
            form_data[f'field_{field.id}_required'] = 'on' if field.name == 'year' else ''
            form_data[f'field_{field.id}_help_text'] = f'Help for {field.label}'
            form_data[f'field_{field.id}_order'] = field.order
        
        response = self.client.post(reverse('dataset_field_config', args=[self.dataset.id]), form_data)
        self.assertEqual(response.status_code, 302)
        
        # 4. Verify changes were saved
        updated_fields = CustomField.objects.filter(dataset=self.dataset, is_standard_field=True)
        for field in updated_fields:
            field.refresh_from_db()
            self.assertEqual(field.label, f'Updated {field.label}')
            self.assertTrue(field.enabled)
    
    def test_field_configuration_display_in_dataset_detail(self):
        """Test that field configuration is properly displayed in dataset detail"""
        from datasets.models import CustomField
        
        # Create custom fields with custom values
        CustomField.objects.create(
            dataset=self.dataset,
            name='custom_field_1',
            label='Custom Field 1',
            field_type='text',
            is_standard_field=False,
            enabled=True,
            required=False
        )
        CustomField.objects.create(
            dataset=self.dataset,
            name='custom_field_2',
            label='Custom Field 2',
            field_type='integer',
            is_standard_field=False,
            enabled=False,
            required=True
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dataset_detail', args=[self.dataset.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Custom Field 1')
        self.assertContains(response, 'Custom Field 2')
        self.assertContains(response, 'Configure All Fields')
    
    def test_field_configuration_permissions(self):
        """Test that only dataset owners can configure fields"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Create a field config for the dataset
        config = DatasetFieldConfig.objects.create(dataset=self.dataset)
        
        # Other user should not be able to access field configuration
        self.client.login(username='otheruser', password='otherpass123')
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 403)
        
        # Other user should not be able to POST to field configuration
        form_data = {
            'usage_code1_label': 'Hacked Usage',
            'usage_code1_enabled': True,
            'usage_code2_label': 'Usage 2',
            'usage_code2_enabled': True,
            'usage_code3_label': 'Usage 3',
            'usage_code3_enabled': True,
            'cat_inno_label': 'Innovation',
            'cat_inno_enabled': True,
            'cat_wert_label': 'Value',
            'cat_wert_enabled': True,
            'cat_fili_label': 'Filial',
            'cat_fili_enabled': True,
            'year_label': 'Year',
            'year_enabled': True,
            'name_label': 'Name',
            'name_enabled': True
        }
        
        response = self.client.post(reverse('dataset_field_config', args=[self.dataset.id]), form_data)
        self.assertEqual(response.status_code, 403)
        
        # Original configuration should remain unchanged
        config.refresh_from_db()
        self.assertEqual(config.usage_code1_label, 'Usage Code 1')  # Default value


class CustomFieldModelTest(TestCase):
    """Test cases for CustomField model"""
    
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
    
    def test_custom_field_creation(self):
        """Test creating a CustomField"""
        field = CustomField.objects.create(
            dataset=self.dataset,
            name='test_field',
            label='Test Field',
            field_type='text',
            required=True,
            enabled=True,
            help_text='This is a test field',
            order=1
        )
        
        self.assertEqual(field.dataset, self.dataset)
        self.assertEqual(field.name, 'test_field')
        self.assertEqual(field.label, 'Test Field')
        self.assertEqual(field.field_type, 'text')
        self.assertTrue(field.required)
        self.assertTrue(field.enabled)
        self.assertEqual(field.help_text, 'This is a test field')
        self.assertEqual(field.order, 1)
    
    def test_custom_field_str(self):
        """Test string representation of CustomField"""
        field = CustomField.objects.create(
            dataset=self.dataset,
            name='test_field',
            label='Test Field',
            field_type='text'
        )
        expected_str = f"Test Field ({self.dataset.name})"
        self.assertEqual(str(field), expected_str)
    
    def test_custom_field_choices_list(self):
        """Test get_choices_list method"""
        field = CustomField.objects.create(
            dataset=self.dataset,
            name='choice_field',
            label='Choice Field',
            field_type='choice',
            choices='Option 1, Option 2, Option 3'
        )
        
        choices = field.get_choices_list()
        self.assertEqual(choices, ['Option 1', 'Option 2', 'Option 3'])
    
    def test_custom_field_choices_list_empty(self):
        """Test get_choices_list method with empty choices"""
        field = CustomField.objects.create(
            dataset=self.dataset,
            name='text_field',
            label='Text Field',
            field_type='text'
        )
        
        choices = field.get_choices_list()
        self.assertEqual(choices, [])
    
    def test_custom_field_unique_constraint(self):
        """Test unique constraint on dataset and name"""
        CustomField.objects.create(
            dataset=self.dataset,
            name='test_field',
            label='Test Field',
            field_type='text'
        )
        
        # Try to create another field with same name for same dataset
        with self.assertRaises(IntegrityError):
            CustomField.objects.create(
                dataset=self.dataset,
                name='test_field',
                label='Another Test Field',
                field_type='integer'
            )
    
    def test_custom_field_cascade_delete(self):
        """Test that custom fields are deleted when dataset is deleted"""
        field = CustomField.objects.create(
            dataset=self.dataset,
            name='test_field',
            label='Test Field',
            field_type='text'
        )
        field_id = field.id
        
        # Delete the dataset
        self.dataset.delete()
        
        # Check that the custom field is also deleted
        self.assertFalse(CustomField.objects.filter(id=field_id).exists())


class CustomFieldFormTest(TestCase):
    """Test cases for CustomFieldForm"""
    
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
    
    def test_form_validation_valid_data(self):
        """Test form validation with valid data"""
        form_data = {
            'name': 'test_field',
            'label': 'Test Field',
            'field_type': 'text',
            'required': True,
            'enabled': True,
            'help_text': 'This is a test field',
            'order': 1
        }
        
        from .views import CustomFieldForm
        form = CustomFieldForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_form_validation_choice_field_with_choices(self):
        """Test form validation for choice field with choices"""
        form_data = {
            'name': 'choice_field',
            'label': 'Choice Field',
            'field_type': 'choice',
            'required': True,
            'enabled': True,
            'choices': 'Option 1, Option 2, Option 3',
            'order': 1
        }
        
        from .views import CustomFieldForm
        form = CustomFieldForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_form_validation_choice_field_without_choices(self):
        """Test form validation for choice field without choices"""
        form_data = {
            'name': 'choice_field',
            'label': 'Choice Field',
            'field_type': 'choice',
            'required': True,
            'enabled': True,
            'choices': '',
            'order': 1
        }
        
        from .views import CustomFieldForm
        form = CustomFieldForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('choices', form.errors)
    
    def test_form_name_cleaning(self):
        """Test form name cleaning functionality"""
        from .views import CustomFieldForm
        
        # Test with spaces and special characters
        form_data = {
            'name': 'Test Field Name!',
            'label': 'Test Field',
            'field_type': 'text',
            'required': False,
            'enabled': True,
            'order': 1
        }
        
        form = CustomFieldForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['name'], 'test_field_name')
    
    def test_form_name_cleaning_starts_with_number(self):
        """Test form name cleaning when name starts with number"""
        from .views import CustomFieldForm
        
        form_data = {
            'name': '123field',
            'label': 'Test Field',
            'field_type': 'text',
            'required': False,
            'enabled': True,
            'order': 1
        }
        
        form = CustomFieldForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['name'], 'field_123field')


class CustomFieldViewTest(TestCase):
    """Test cases for custom field views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        self.dataset = DataSet.objects.create(
            name='Test Dataset',
            description='Test Description',
            owner=self.user
        )
        self.custom_field = CustomField.objects.create(
            dataset=self.dataset,
            name='test_field',
            label='Test Field',
            field_type='text',
            required=True,
            enabled=True
        )
    
    def test_dataset_field_config_view_get(self):
        """Test GET request to custom fields management view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('custom_fields', response.context)
        self.assertIn('dataset', response.context)
        self.assertEqual(response.context['dataset'], self.dataset)
    
    def test_dataset_field_config_view_unauthorized_user(self):
        """Test that unauthorized users cannot access custom fields management"""
        self.client.login(username='otheruser', password='otherpass123')
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        
        self.assertEqual(response.status_code, 403)
    
    def test_custom_field_create_view_get(self):
        """Test GET request to custom field creation view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('custom_field_create', args=[self.dataset.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('dataset', response.context)
    
    def test_custom_field_create_view_post_valid(self):
        """Test POST request with valid data to custom field creation view"""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': 'new_field',
            'label': 'New Field',
            'field_type': 'text',
            'required': False,
            'enabled': True,
            'help_text': 'This is a new field',
            'order': 2
        }
        
        response = self.client.post(reverse('custom_field_create', args=[self.dataset.id]), form_data)
        
        # Should redirect to custom fields management
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dataset_field_config', args=[self.dataset.id]))
        
        # Check that the custom field was created
        self.assertTrue(CustomField.objects.filter(dataset=self.dataset, name='new_field').exists())
    
    def test_custom_field_edit_view_get(self):
        """Test GET request to custom field edit view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('custom_field_edit', args=[self.dataset.id, self.custom_field.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('custom_field', response.context)
    
    def test_custom_field_edit_view_post_valid(self):
        """Test POST request with valid data to custom field edit view"""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': 'updated_field',
            'label': 'Updated Field',
            'field_type': 'integer',
            'required': True,
            'enabled': True,
            'help_text': 'This is an updated field',
            'order': 3
        }
        
        response = self.client.post(reverse('custom_field_edit', args=[self.dataset.id, self.custom_field.id]), form_data)
        
        # Should redirect to custom fields management
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dataset_field_config', args=[self.dataset.id]))
        
        # Check that the custom field was updated
        updated_field = CustomField.objects.get(id=self.custom_field.id)
        self.assertEqual(updated_field.label, 'Updated Field')
        self.assertEqual(updated_field.field_type, 'integer')
    
    def test_custom_field_delete_view_get(self):
        """Test GET request to custom field delete view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('custom_field_delete', args=[self.dataset.id, self.custom_field.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('custom_field', response.context)
        self.assertEqual(response.context['custom_field'], self.custom_field)
    
    def test_custom_field_delete_view_post(self):
        """Test POST request to custom field delete view"""
        self.client.login(username='testuser', password='testpass123')
        
        field_id = self.custom_field.id
        response = self.client.post(reverse('custom_field_delete', args=[self.dataset.id, self.custom_field.id]))
        
        # Should redirect to custom fields management
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dataset_field_config', args=[self.dataset.id]))
        
        # Check that the custom field was deleted
        self.assertFalse(CustomField.objects.filter(id=field_id).exists())
    
    def test_custom_field_views_unauthorized_user(self):
        """Test that unauthorized users cannot access custom field views"""
        self.client.login(username='otheruser', password='otherpass123')
        
        # Test all custom field views
        views_to_test = [
            ('dataset_field_config', [self.dataset.id]),
            ('custom_field_create', [self.dataset.id]),
            ('custom_field_edit', [self.dataset.id, self.custom_field.id]),
            ('custom_field_delete', [self.dataset.id, self.custom_field.id]),
        ]
        
        for view_name, args in views_to_test:
            response = self.client.get(reverse(view_name, args=args))
            self.assertEqual(response.status_code, 403)
    
    def test_custom_field_views_unauthenticated(self):
        """Test that unauthenticated users cannot access custom field views"""
        views_to_test = [
            ('dataset_field_config', [self.dataset.id]),
            ('custom_field_create', [self.dataset.id]),
            ('custom_field_edit', [self.dataset.id, self.custom_field.id]),
            ('custom_field_delete', [self.dataset.id, self.custom_field.id]),
        ]
        
        for view_name, args in views_to_test:
            response = self.client.get(reverse(view_name, args=args))
            self.assertEqual(response.status_code, 302)  # Redirect to login


class CustomFieldIntegrationTest(TestCase):
    """Integration tests for custom fields feature"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
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
    
    def test_custom_fields_display_in_dataset_detail(self):
        """Test that custom fields are displayed in dataset detail view"""
        # Create some custom fields
        field1 = CustomField.objects.create(
            dataset=self.dataset,
            name='field1',
            label='Field 1',
            field_type='text',
            required=True,
            enabled=True,
            help_text='First custom field',
            order=1
        )
        
        field2 = CustomField.objects.create(
            dataset=self.dataset,
            name='field2',
            label='Field 2',
            field_type='choice',
            required=False,
            enabled=True,
            choices='Option A, Option B, Option C',
            order=2
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dataset_detail', args=[self.dataset.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Field 1')
        self.assertContains(response, 'Field 2')
        self.assertContains(response, 'Configure All Fields')
    
    def test_custom_fields_workflow(self):
        """Test complete workflow of managing custom fields"""
        self.client.login(username='testuser', password='testpass123')
        
        # 1. View dataset detail (should show no custom fields initially)
        response = self.client.get(reverse('dataset_detail', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No custom fields configured')
        
        # 2. Access custom fields management
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No Custom Fields')
        
        # 3. Create a custom field
        form_data = {
            'name': 'test_field',
            'label': 'Test Field',
            'field_type': 'text',
            'required': True,
            'enabled': True,
            'help_text': 'This is a test field',
            'order': 1
        }
        
        response = self.client.post(reverse('custom_field_create', args=[self.dataset.id]), form_data)
        self.assertEqual(response.status_code, 302)
        
        # 4. Verify the field was created
        self.assertTrue(CustomField.objects.filter(dataset=self.dataset, name='test_field').exists())
        
        # 5. View custom fields management (should show the new field)
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Field')
        self.assertContains(response, 'This is a test field')
        
        # 6. Edit the custom field
        field = CustomField.objects.get(dataset=self.dataset, name='test_field')
        edit_data = {
            'name': 'updated_field',
            'label': 'Updated Field',
            'field_type': 'integer',
            'required': False,
            'enabled': True,
            'help_text': 'This is an updated field',
            'order': 2
        }
        
        response = self.client.post(reverse('custom_field_edit', args=[self.dataset.id, field.id]), edit_data)
        self.assertEqual(response.status_code, 302)
        
        # 7. Verify the field was updated
        updated_field = CustomField.objects.get(id=field.id)
        self.assertEqual(updated_field.label, 'Updated Field')
        self.assertEqual(updated_field.field_type, 'integer')
        
        # 8. Delete the custom field
        response = self.client.post(reverse('custom_field_delete', args=[self.dataset.id, field.id]))
        self.assertEqual(response.status_code, 302)
        
        # 9. Verify the field was deleted
        self.assertFalse(CustomField.objects.filter(id=field.id).exists())
    
    def test_custom_fields_permissions(self):
        """Test that only dataset owners can manage custom fields"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Other user should not be able to access custom field management
        self.client.login(username='otheruser', password='otherpass123')
        
        views_to_test = [
            ('dataset_field_config', [self.dataset.id]),
            ('custom_field_create', [self.dataset.id]),
        ]
        
        for view_name, args in views_to_test:
            response = self.client.get(reverse(view_name, args=args))
            self.assertEqual(response.status_code, 403)
        
        # Other user should not be able to POST to custom field management
        form_data = {
            'name': 'hacked_field',
            'label': 'Hacked Field',
            'field_type': 'text',
            'required': True,
            'enabled': True
        }
        
        response = self.client.post(reverse('custom_field_create', args=[self.dataset.id]), form_data)
        self.assertEqual(response.status_code, 403)
        
        # No custom fields should be created
        self.assertFalse(CustomField.objects.filter(dataset=self.dataset).exists())
