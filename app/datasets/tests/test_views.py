from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from ..models import DataSet, DatasetFieldConfig, DataGeometry, DataEntry, DataEntryField, Typology, TypologyEntry, DatasetField
from ..views import DatasetFieldConfigForm, DatasetFieldForm, GroupForm


class DatasetFieldConfigViewTest(TestCase):
    """Test cases for DatasetFieldConfig views"""
    
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
        self.config = DatasetFieldConfig.objects.create(dataset=self.dataset)
    
    def test_dataset_field_config_view_unauthenticated(self):
        """Test that unauthenticated users cannot access field configuration"""
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_dataset_field_config_view_unauthorized_user(self):
        """Test that unauthorized users cannot access field configuration"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        self.client.login(username='otheruser', password='otherpass123')
        
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 403)
    
    def test_dataset_field_config_view_get(self):
        """Test GET request to field configuration view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('dataset', response.context)
        self.assertIn('all_fields', response.context)
        self.assertEqual(response.context['dataset'], self.dataset)
    
    def test_dataset_field_config_view_post_valid(self):
        """Test POST request with valid data to field configuration view"""
        self.client.login(username='testuser', password='testpass123')
        
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
        
        response = self.client.post(reverse('dataset_field_config', args=[self.dataset.id]), form_data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful update
        
        # Verify the config was updated
        self.config.refresh_from_db()
        self.assertEqual(self.config.usage_code1_label, 'Updated Usage 1')
        self.assertFalse(self.config.usage_code1_enabled)
    
    def test_dataset_field_config_view_nonexistent_dataset(self):
        """Test field configuration view with nonexistent dataset"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dataset_field_config', args=[999]))
        self.assertEqual(response.status_code, 404)


class DatasetFieldViewTest(TestCase):
    """Test cases for DatasetField views"""
    
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
        self.custom_field = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='test_field',
            label='Test Field',
            field_type='text',
            required=True,
            enabled=True
        )
    
    def test_custom_field_views_unauthenticated(self):
        """Test that unauthenticated users cannot access custom field views"""
        # Test create view
        response = self.client.get(reverse('custom_field_create', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 302)
        
        # Test edit view
        response = self.client.get(reverse('custom_field_edit', args=[self.dataset.id, self.custom_field.id]))
        self.assertEqual(response.status_code, 302)
        
        # Test delete view
        response = self.client.get(reverse('custom_field_delete', args=[self.dataset.id, self.custom_field.id]))
        self.assertEqual(response.status_code, 302)
    
    def test_custom_field_views_unauthorized_user(self):
        """Test that unauthorized users cannot access custom field views"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        self.client.login(username='otheruser', password='otherpass123')
        
        # Test create view
        response = self.client.get(reverse('custom_field_create', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 403)
        
        # Test edit view
        response = self.client.get(reverse('custom_field_edit', args=[self.dataset.id, self.custom_field.id]))
        self.assertEqual(response.status_code, 403)
        
        # Test delete view
        response = self.client.get(reverse('custom_field_delete', args=[self.dataset.id, self.custom_field.id]))
        self.assertEqual(response.status_code, 403)
    
    def test_custom_field_create_view_get(self):
        """Test GET request to custom field creation view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('custom_field_create', args=[self.dataset.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('dataset', response.context)
        self.assertEqual(response.context['dataset'], self.dataset)
    
    def test_custom_field_create_view_post_valid(self):
        """Test POST request with valid data to custom field creation view"""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'field_name': 'new_field',
            'label': 'New Field',
            'field_type': 'integer',
            'required': False,
            'enabled': True,
            'help_text': 'This is a new field',
            'order': 2
        }
        
        response = self.client.post(reverse('custom_field_create', args=[self.dataset.id]), form_data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        
        # Verify the field was created
        self.assertTrue(DatasetField.objects.filter(dataset=self.dataset, field_name='new_field').exists())
    
    def test_custom_field_edit_view_get(self):
        """Test GET request to custom field edit view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('custom_field_edit', args=[self.dataset.id, self.custom_field.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('dataset', response.context)
        self.assertEqual(response.context['dataset'], self.dataset)
    
    def test_custom_field_edit_view_post_valid(self):
        """Test POST request with valid data to custom field edit view"""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'field_name': 'updated_field',
            'label': 'Updated Field',
            'field_type': 'text',
            'required': False,
            'enabled': True,
            'help_text': 'Updated help text',
            'order': 3
        }
        
        response = self.client.post(reverse('custom_field_edit', args=[self.dataset.id, self.custom_field.id]), form_data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful update
        
        # Verify the field was updated
        self.custom_field.refresh_from_db()
        self.assertEqual(self.custom_field.label, 'Updated Field')
        self.assertEqual(self.custom_field.field_type, 'text')
    
    def test_custom_field_delete_view_get(self):
        """Test GET request to custom field delete view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('custom_field_delete', args=[self.dataset.id, self.custom_field.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('custom_field', response.context)
        self.assertIn('dataset', response.context)
        self.assertEqual(response.context['custom_field'], self.custom_field)
        self.assertEqual(response.context['dataset'], self.dataset)
    
    def test_custom_field_delete_view_post(self):
        """Test POST request to custom field delete view"""
        self.client.login(username='testuser', password='testpass123')
        
        field_id = self.custom_field.id
        response = self.client.post(reverse('custom_field_delete', args=[self.dataset.id, self.custom_field.id]))
        self.assertEqual(response.status_code, 302)  # Redirect after successful deletion
        
        # Verify the field was deleted
        self.assertFalse(DatasetField.objects.filter(id=field_id).exists())
    
    def test_dataset_field_config_view_get(self):
        """Test GET request to custom fields management view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('dataset', response.context)
        self.assertIn('all_fields', response.context)
        self.assertEqual(response.context['dataset'], self.dataset)
    
    def test_dataset_field_config_view_unauthorized_user(self):
        """Test that unauthorized users cannot access custom fields management"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        self.client.login(username='otheruser', password='otherpass123')
        
        response = self.client.get(reverse('dataset_field_config', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 403)
