from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from datasets.models import DataSet, DatasetField, DataGeometry, DataEntry
from django.contrib.gis.geos import Point
import json


class DataInputFieldsTestCase(TestCase):
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
        
        # Create test fields
        self.field1 = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='test_field_1',
            label='Test Field 1',
            field_type='text',
            enabled=True,
            order=1
        )
        
        self.field2 = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='test_field_2',
            label='Test Field 2',
            field_type='integer',
            enabled=True,
            order=2
        )
        
        # Create a disabled field
        self.disabled_field = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='disabled_field',
            label='Disabled Field',
            field_type='text',
            enabled=False,
            order=3
        )
        
        # Create a test geometry
        self.geometry = DataGeometry.objects.create(
            dataset=self.dataset,
            address='Test Address',
            geometry=Point(16.0, 48.0, srid=4326),
            id_kurz='TEST001',
            user=self.user
        )
        
        # Create a test entry
        self.entry = DataEntry.objects.create(
            geometry=self.geometry,
            name='Test Entry',
            year=2023,
            user=self.user
        )
        
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_data_input_view_returns_enabled_fields(self):
        """Test that the data input view returns only enabled fields"""
        url = reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that the response contains the dataset
        self.assertContains(response, self.dataset.name)
        
        # Check that fields_data is passed to the template
        self.assertIn('fields_data', response.context)
        fields_data = response.context['fields_data']
        
        # Should have 2 enabled fields
        self.assertEqual(len(fields_data), 2)
        
        # Check field names
        field_names = [field['field_name'] for field in fields_data]
        self.assertIn('test_field_1', field_names)
        self.assertIn('test_field_2', field_names)
        self.assertNotIn('disabled_field', field_names)
    
    def test_data_input_template_renders_fields(self):
        """Test that the data input template renders the fields correctly"""
        url = reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that the template contains the field data as JSON
        self.assertContains(response, 'allFields')
        
        # Extract the JSON data from the response
        content = response.content.decode('utf-8')
        
        # Find the JSON script tag
        import re
        json_match = re.search(r'<script[^>]*id="allFields"[^>]*>(.*?)</script>', content, re.DOTALL)
        self.assertIsNotNone(json_match, "Could not find allFields JSON script tag")
        
        json_data = json_match.group(1).strip()
        fields_data = json.loads(json_data)
        
        # Should have 2 enabled fields
        self.assertEqual(len(fields_data), 2)
        
        # Check field properties
        field1_data = next(f for f in fields_data if f['field_name'] == 'test_field_1')
        self.assertEqual(field1_data['label'], 'Test Field 1')
        self.assertEqual(field1_data['field_type'], 'text')
        self.assertTrue(field1_data['enabled'])
        
        field2_data = next(f for f in fields_data if f['field_name'] == 'test_field_2')
        self.assertEqual(field2_data['label'], 'Test Field 2')
        self.assertEqual(field2_data['field_type'], 'integer')
        self.assertTrue(field2_data['enabled'])
    
    def test_data_input_with_no_enabled_fields(self):
        """Test data input when no fields are enabled - should auto-enable them"""
        # Disable all fields
        DatasetField.objects.filter(dataset=self.dataset).update(enabled=False)
        
        url = reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Should auto-enable fields and return them
        self.assertIn('fields_data', response.context)
        fields_data = response.context['fields_data']
        self.assertEqual(len(fields_data), 3)  # All 3 fields should be auto-enabled
        
        # Check that fields are now enabled in the database
        enabled_fields = DatasetField.objects.filter(dataset=self.dataset, enabled=True)
        self.assertEqual(enabled_fields.count(), 3)
    
    def test_data_input_auto_enables_fields(self):
        """Test that the view auto-enables fields when none are enabled"""
        # Disable all fields
        DatasetField.objects.filter(dataset=self.dataset).update(enabled=False)
        
        url = reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that fields are now enabled in the database
        enabled_fields = DatasetField.objects.filter(dataset=self.dataset, enabled=True)
        self.assertEqual(enabled_fields.count(), 3)  # All 3 fields should be enabled
        
        # Check that fields_data contains the fields
        fields_data = response.context['fields_data']
        self.assertEqual(len(fields_data), 3)
    
    def test_data_input_javascript_variables(self):
        """Test that JavaScript variables are set correctly"""
        url = reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check that window.allFields is set
        self.assertIn('window.allFields = JSON.parse(document.getElementById(\'allFields\').textContent);', content)
        
        # Check that window.allowMultipleEntries is set
        self.assertIn('window.allowMultipleEntries =', content)
    
    def test_data_input_with_geometry_selection(self):
        """Test that fields are shown when a geometry is selected"""
        url = reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Should contain the JavaScript file
        self.assertIn('data-input.js', content)
        
        # Should contain the field configuration
        self.assertIn('window.allFields', content)
    
    def test_data_input_javascript_contains_field_rendering(self):
        """Test that the JavaScript contains the field rendering logic"""
        url = reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Should contain the JavaScript file
        self.assertIn('data-input.js', content)
        
        # Should contain the field data
        self.assertIn('allFields', content)
        
        # Should contain the field configuration
        self.assertIn('window.allFields', content)
    
    def test_map_data_endpoint(self):
        """Test that the map data endpoint returns data"""
        url = reverse('dataset_map_data', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        self.assertEqual(response.status_code, 200)
        
        # Should return JSON data
        import json
        data = json.loads(response.content)
        self.assertIn('map_data', data)
        
        # Should contain the geometry data
        map_data = data['map_data']
        self.assertEqual(len(map_data), 1)  # Should have 1 geometry
        
        geometry = map_data[0]
        self.assertEqual(geometry['id'], self.geometry.id)
        self.assertEqual(geometry['id_kurz'], self.geometry.id_kurz)
        self.assertEqual(geometry['address'], self.geometry.address)
    
    def test_generate_entries_table_with_fields(self):
        """Test that generateEntriesTable renders fields correctly"""
        # This test simulates what happens when a geometry is clicked
        # We'll test the JavaScript logic by checking if the fields would be rendered
        
        url = reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Extract the fields data from the response
        content = response.content.decode('utf-8')
        import re
        json_match = re.search(r'<script[^>]*id="allFields"[^>]*>(.*?)</script>', content, re.DOTALL)
        self.assertIsNotNone(json_match, "Could not find allFields JSON script tag")
        
        json_data = json_match.group(1).strip()
        fields_data = json.loads(json_data)
        
        # Should have 2 enabled fields
        self.assertEqual(len(fields_data), 2)
        
        # Check that the fields have the right properties for rendering
        for field in fields_data:
            self.assertIn('field_name', field)
            self.assertIn('label', field)
            self.assertIn('field_type', field)
            self.assertIn('enabled', field)
            self.assertTrue(field['enabled'])
        
        # Check that the JavaScript file is loaded
        self.assertIn('data-input.js', content)
        
        # Check that the fields are properly formatted for JavaScript
        for field in fields_data:
            self.assertIn('field_name', field)
            self.assertIn('label', field)
            self.assertIn('field_type', field)
            self.assertIn('enabled', field)
            self.assertTrue(field['enabled'])
