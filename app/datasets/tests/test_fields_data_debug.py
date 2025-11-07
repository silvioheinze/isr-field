from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
import json

from ..models import DataSet, DataGeometry, DataEntry, DataEntryField, DatasetField


class FieldsDataDebugTestCase(TestCase):
    """Debug test to check why fields_data is empty"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.dataset = DataSet.objects.create(
            name='Test Dataset',
            description='Test dataset for debugging',
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
    
    def test_fields_data_in_template_context(self):
        """Test that fields_data is properly passed to the template"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        # Check that fields_data is in the context
        self.assertIn('fields_data', response.context)
        fields_data = response.context['fields_data']
        
        print(f"fields_data length: {len(fields_data)}")
        print(f"fields_data content: {fields_data}")
        
        # Should include our custom fields among the standard ones
        self.assertGreaterEqual(len(fields_data), 2)
        field_map = {field['field_name']: field for field in fields_data}
        
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
    
    def test_allFields_script_tag_in_template(self):
        """Test that the allFields script tag is properly rendered"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check that the allFields script tag exists
        self.assertIn('id="allFields"', content)
        
        # Extract the JSON content
        import re
        json_match = re.search(r'<script[^>]*id="allFields"[^>]*>(.*?)</script>', content, re.DOTALL)
        self.assertIsNotNone(json_match, "allFields script tag not found")
        
        fields_json = json_match.group(1).strip()
        print(f"Fields JSON: {fields_json}")
        
        # Parse the JSON
        fields_data = json.loads(fields_json)
        print(f"Parsed fields_data: {fields_data}")
        
        # Should include our custom fields
        self.assertGreaterEqual(len(fields_data), 2)
        
        # Check that fields are properly structured
        field_names = {field['field_name'] for field in fields_data}
        self.assertIn('test_field_1', field_names)
        self.assertIn('test_field_2', field_names)
    
    def test_window_allFields_initialization(self):
        """Test that window.allFields is properly initialized in the template"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check that the initialization code is present
        self.assertIn('window.allFields = JSON.parse(allFieldsElement.textContent);', content)
        self.assertIn('console.log(\'window.allFields initialized:\', window.allFields);', content)
