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
        self.assertGreaterEqual(len(fields_data), 3)
        
        # Check that our original fields are now enabled in the database
        enabled_fields = DatasetField.objects.filter(
            dataset=self.dataset,
            field_name__in=['test_field_1', 'test_field_2', 'disabled_field'],
            enabled=True
        )
        self.assertEqual(enabled_fields.count(), 3)
    
    def test_data_input_auto_enables_fields(self):
        """Test that the view auto-enables fields when none are enabled"""
        # Disable all fields
        DatasetField.objects.filter(dataset=self.dataset).update(enabled=False)
        
        url = reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that fields are now enabled in the database
        enabled_fields = DatasetField.objects.filter(
            dataset=self.dataset,
            field_name__in=['test_field_1', 'test_field_2', 'disabled_field'],
            enabled=True
        )
        self.assertEqual(enabled_fields.count(), 3)
        
        # Check that fields_data contains at least our fields
        fields_data = response.context['fields_data']
        field_names = {field['field_name'] for field in fields_data}
        for name in ['test_field_1', 'test_field_2', 'disabled_field']:
            self.assertIn(name, field_names)
    
    def test_data_input_javascript_variables(self):
        """Test that JavaScript variables are set correctly"""
        url = reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Check that window.allFields is set
        self.assertIn('window.allFields = JSON.parse(allFieldsElement.textContent);', content)
        
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
        
        field_names = {field['field_name'] for field in fields_data}
        self.assertIn('test_field_1', field_names)
        self.assertIn('test_field_2', field_names)
        self.assertNotIn('disabled_field', field_names)
    
    def test_non_editable_field_in_fields_data(self):
        """Test that non_editable property is included in fields_data"""
        # Create a non-editable field
        non_editable_field = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='non_editable_field',
            label='Non-Editable Field',
            field_type='text',
            enabled=True,
            non_editable=True,
            order=4
        )
        
        url = reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check that fields_data is passed to the template
        self.assertIn('fields_data', response.context)
        fields_data = response.context['fields_data']
        
        # Find the non-editable field in the data
        non_editable_data = next(
            (f for f in fields_data if f['field_name'] == 'non_editable_field'),
            None
        )
        self.assertIsNotNone(non_editable_data, "Non-editable field not found in fields_data")
        self.assertTrue(non_editable_data['non_editable'], "non_editable property should be True")
        
        # Check that editable field has non_editable=False
        editable_data = next(
            (f for f in fields_data if f['field_name'] == 'test_field_1'),
            None
        )
        self.assertIsNotNone(editable_data, "Editable field not found in fields_data")
        self.assertFalse(editable_data.get('non_editable', False), "non_editable property should be False for editable field")
    
    def test_non_editable_field_in_json_output(self):
        """Test that non_editable property is included in the JSON output for JavaScript"""
        # Create a non-editable field
        non_editable_field = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='non_editable_field',
            label='Non-Editable Field',
            field_type='text',
            enabled=True,
            non_editable=True,
            order=4
        )
        
        url = reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Extract the JSON data from the response
        content = response.content.decode('utf-8')
        import re
        json_match = re.search(r'<script[^>]*id="allFields"[^>]*>(.*?)</script>', content, re.DOTALL)
        self.assertIsNotNone(json_match, "Could not find allFields JSON script tag")
        
        json_data = json_match.group(1).strip()
        fields_data = json.loads(json_data)
        
        # Find the non-editable field in the JSON
        non_editable_data = next(
            (f for f in fields_data if f['field_name'] == 'non_editable_field'),
            None
        )
        self.assertIsNotNone(non_editable_data, "Non-editable field not found in JSON")
        self.assertTrue(non_editable_data['non_editable'], "non_editable property should be True in JSON")
        
        # Verify that editable fields have non_editable=False or missing
        editable_data = next(
            (f for f in fields_data if f['field_name'] == 'test_field_1'),
            None
        )
        self.assertIsNotNone(editable_data, "Editable field not found in JSON")
        self.assertFalse(editable_data.get('non_editable', False), "non_editable property should be False for editable field in JSON")
    
    def test_dataset_fields_api_includes_non_editable(self):
        """Test that the dataset_fields API endpoint includes non_editable property"""
        # Create a non-editable field
        non_editable_field = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='non_editable_field',
            label='Non-Editable Field',
            field_type='text',
            enabled=True,
            non_editable=True,
            order=4
        )
        
        url = reverse('dataset_fields', kwargs={'dataset_id': self.dataset.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        data = json.loads(response.content)
        self.assertIn('fields', data)
        
        fields_data = data['fields']
        
        # Find the non-editable field
        non_editable_data = next(
            (f for f in fields_data if f['field_name'] == 'non_editable_field'),
            None
        )
        self.assertIsNotNone(non_editable_data, "Non-editable field not found in API response")
        self.assertTrue(non_editable_data['non_editable'], "non_editable property should be True in API response")
        
        # Verify that editable fields have non_editable=False
        editable_data = next(
            (f for f in fields_data if f['field_name'] == 'test_field_1'),
            None
        )
        self.assertIsNotNone(editable_data, "Editable field not found in API response")
        self.assertFalse(editable_data.get('non_editable', False), "non_editable property should be False for editable field in API response")
