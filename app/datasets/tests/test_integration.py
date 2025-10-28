from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from ..models import DataSet, DatasetFieldConfig, DataGeometry, DataEntry, DataEntryField, Typology, TypologyEntry, DatasetField
from ..views import DatasetFieldConfigForm, DatasetFieldForm, GroupForm


class DatasetFieldConfigIntegrationTest(TestCase):
    """Integration tests for DatasetFieldConfig feature"""
    
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
        from datasets.models import DatasetField
        
        # Initially no standard fields should exist
        self.assertFalse(DatasetField.objects.filter(dataset=self.dataset).exists())
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dataset_detail', args=[self.dataset.id]))
        
        # After viewing dataset detail, standard fields should be created
        self.assertTrue(DatasetField.objects.filter(dataset=self.dataset).exists())
        standard_fields = DatasetField.objects.filter(dataset=self.dataset)
        
        # Check that we have the expected standard fields
        field_names = [field.field_name for field in standard_fields]
        expected_fields = ['name', 'usage_code1', 'usage_code2', 'usage_code3', 'cat_inno', 'cat_wert', 'cat_fili', 'year']
        for expected_field in expected_fields:
            self.assertIn(expected_field, field_names)
    
    def test_field_configuration_workflow(self):
        """Test complete workflow of configuring dataset fields"""
        self.client.login(username='testuser', password='testpass123')
        
        # 1. View dataset detail (should create standard fields)
        response = self.client.get(reverse('dataset_detail', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(DatasetField.objects.filter(dataset=self.dataset).exists())
        
        # 2. View field configuration page
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('all_fields', response.context)
        
        # 3. Update field configuration
        all_fields = DatasetField.objects.filter(dataset=self.dataset)
        form_data = {}
        for field in all_fields:
            form_data[f'field_{field.id}_enabled'] = 'on'
            form_data[f'field_{field.id}_required'] = 'on' if field.field_name == 'year' else ''
            form_data[f'field_{field.id}_help_text'] = f'Help for {field.label}'
            form_data[f'field_{field.id}_order'] = field.order
        
        response = self.client.post(reverse('dataset_field_config', args=[self.dataset.id]), form_data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful update
        
        # 4. Verify fields were updated
        for field in all_fields:
            field.refresh_from_db()
            self.assertTrue(field.enabled)
            if field.field_name == 'year':
                self.assertTrue(field.required)
            else:
                self.assertFalse(field.required)
    
    def test_field_configuration_display_in_dataset_detail(self):
        """Test that field configuration is properly displayed in dataset detail"""
        # Create some custom fields
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='custom_field_1',
            label='Custom Field 1',
            field_type='text',
            enabled=True,
            required=False
        )
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='custom_field_2',
            label='Custom Field 2',
            field_type='integer',
            enabled=False,
            required=True
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dataset_detail', args=[self.dataset.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Custom Field 1')
        self.assertContains(response, 'Custom Field 2')
        self.assertContains(response, 'Field Configuration')
    
    def test_field_configuration_permissions(self):
        """Test that only dataset owners can configure fields"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Test unauthorized access
        self.client.login(username='otheruser', password='otherpass123')
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 403)
        
        # Test authorized access
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)


class DatasetFieldIntegrationTest(TestCase):
    """Integration tests for DatasetField feature"""
    
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
    
    def test_custom_fields_workflow(self):
        """Test complete workflow of managing custom fields"""
        self.client.login(username='testuser', password='testpass123')
        
        # 1. View dataset detail (should show no custom fields initially)
        response = self.client.get(reverse('dataset_detail', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No custom fields configured')
        
        # 2. View custom fields management
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        
        # 3. Create a custom field
        response = self.client.get(reverse('custom_field_create', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        
        form_data = {
            'field_name': 'test_field',
            'label': 'Test Field',
            'field_type': 'text',
            'required': True,
            'enabled': True,
            'help_text': 'This is a test field',
            'order': 1
        }
        
        response = self.client.post(reverse('custom_field_create', args=[self.dataset.id]), form_data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        
        # 4. Verify the field was created
        self.assertTrue(DatasetField.objects.filter(dataset=self.dataset, field_name='test_field').exists())
        
        # 5. View custom fields management (should show the new field)
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Field')
        
        # 6. Edit the custom field
        field = DatasetField.objects.get(dataset=self.dataset, field_name='test_field')
        edit_data = {
            'field_name': 'updated_field',
            'label': 'Updated Field',
            'field_type': 'integer',
            'required': False,
            'enabled': True,
            'help_text': 'Updated help text',
            'order': 2
        }
        
        response = self.client.post(reverse('custom_field_edit', args=[self.dataset.id, field.id]), edit_data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful update
        
        # 7. Verify the field was updated
        field.refresh_from_db()
        self.assertEqual(field.label, 'Updated Field')
        self.assertEqual(field.field_type, 'integer')
        self.assertFalse(field.required)
        
        # 8. Delete the custom field
        response = self.client.post(reverse('custom_field_delete', args=[self.dataset.id, field.id]))
        self.assertEqual(response.status_code, 302)  # Redirect after successful deletion
        
        # 9. Verify the field was deleted
        self.assertFalse(DatasetField.objects.filter(id=field.id).exists())
    
    def test_custom_fields_display_in_dataset_detail(self):
        """Test that custom fields are displayed in dataset detail view"""
        # Create some custom fields
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='custom_field_1',
            label='Custom Field 1',
            field_type='text',
            enabled=True,
            required=False
        )
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='custom_field_2',
            label='Custom Field 2',
            field_type='integer',
            enabled=False,
            required=True
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dataset_detail', args=[self.dataset.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Custom Field 1')
        self.assertContains(response, 'Custom Field 2')
        self.assertContains(response, 'Field Configuration')
    
    def test_custom_fields_permissions(self):
        """Test that only dataset owners can manage custom fields"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        # Create a custom field
        field = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='test_field',
            label='Test Field',
            field_type='text'
        )
        
        # Test unauthorized access to various views
        self.client.login(username='otheruser', password='otherpass123')
        
        # Field configuration view
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 403)
        
        # Create field view
        response = self.client.get(reverse('custom_field_create', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 403)
        
        # Edit field view
        response = self.client.get(reverse('custom_field_edit', args=[self.dataset.id, field.id]))
        self.assertEqual(response.status_code, 403)
        
        # Delete field view
        response = self.client.get(reverse('custom_field_delete', args=[self.dataset.id, field.id]))
        self.assertEqual(response.status_code, 403)
