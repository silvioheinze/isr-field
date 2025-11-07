from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
import json

from ..models import DataSet, DataGeometry, DataEntry, DataEntryField, DatasetField


class DatasetFieldsAPITestCase(TestCase):
    """Test the dataset fields API endpoint"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.dataset = DataSet.objects.create(
            name='Test Dataset',
            description='Test dataset for API testing',
            owner=self.user
        )
        
        # Create test fields
        self.field1 = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='test_field_1',
            label='Test Field 1',
            field_type='text',
            enabled=True,
            required=True,
            order=1
        )
        
        self.field2 = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='test_field_2',
            label='Test Field 2',
            field_type='choice',
            enabled=True,
            required=False,
            order=2,
            choices='Option A,Option B,Option C'
        )
        
        # Create a disabled field
        self.field3 = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='disabled_field',
            label='Disabled Field',
            field_type='text',
            enabled=False,
            required=False,
            order=3
        )
    
    def test_dataset_fields_api_returns_enabled_fields(self):
        """Test that the API returns only enabled fields"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_fields', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('fields', data)
        
        fields = data['fields']
        self.assertGreaterEqual(len(fields), 2)
        field_map = {field['field_name']: field for field in fields}
        
        # Check first field
        field1_data = field_map['test_field_1']
        self.assertEqual(field1_data['field_name'], 'test_field_1')
        self.assertEqual(field1_data['label'], 'Test Field 1')
        self.assertTrue(field1_data['enabled'])
        
        # Check second field
        field2_data = field_map['test_field_2']
        self.assertEqual(field2_data['field_name'], 'test_field_2')
        self.assertEqual(field2_data['label'], 'Test Field 2')
        self.assertTrue(field2_data['enabled'])
        
        # Verify disabled field is not included
        field_names = field_map.keys()
        self.assertNotIn('disabled_field', field_names)
    
    def test_dataset_fields_api_with_no_enabled_fields(self):
        """Test API behavior when no fields are enabled"""
        # Disable all fields
        DatasetField.objects.filter(dataset=self.dataset).update(enabled=False)
        
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_fields', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('fields', data)
        
        # Should enable all fields and return them
        fields = data['fields']
        field_names = {field['field_name'] for field in fields}
        for name in ['test_field_1', 'test_field_2', 'disabled_field']:
            self.assertIn(name, field_names)
        
        # Verify all fields are now enabled
        for field in fields:
            self.assertTrue(field['enabled'])
    
    def test_dataset_fields_api_with_no_fields(self):
        """Test API behavior when dataset has no fields"""
        # Remove all fields
        DatasetField.objects.filter(dataset=self.dataset).delete()
        
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_fields', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('fields', data)
        
        # Standard fields should be recreated automatically
        fields = data['fields']
        self.assertGreaterEqual(len(fields), 8)
    
    def test_dataset_fields_api_access_control(self):
        """Test that access control works for the API"""
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        client = Client()
        client.force_login(other_user)
        
        response = client.get(reverse('dataset_fields', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 403)
        
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Access denied')
