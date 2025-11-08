from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.template.loader import render_to_string
from django.template import Context, Template
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
import json
import re

from ..models import DataSet, DataGeometry, DataEntry, DataEntryField, DatasetField


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class DataInputJavaScriptTestCase(TestCase):
    """Test the data input JavaScript functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.dataset = DataSet.objects.create(
            name='Test Dataset',
            description='Test dataset for JavaScript testing',
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
        
        # Create test geometry
        from django.contrib.gis.geos import Point
        self.geometry = DataGeometry.objects.create(
            dataset=self.dataset,
            id_kurz='TEST001',
            address='Test Address',
            geometry=Point(15.0, 48.0),
            user=self.user
        )
        
        # Create test entry
        self.entry = DataEntry.objects.create(
            geometry=self.geometry,
            name='Test Entry',
            year=2023,
            user=self.user
        )
        
        # Create field values
        DataEntryField.objects.create(
            entry=self.entry,
            field_name='test_field_1',
            value='Test Value 1'
        )
        
        DataEntryField.objects.create(
            entry=self.entry,
            field_name='test_field_2',
            value='Option A'
        )
    
    def test_data_input_template_renders_correctly(self):
        """Test that the data input template renders with correct field data"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        # Check that the template contains the field data
        self.assertContains(response, 'window.allFields')
        self.assertContains(response, 'test_field_1')
        self.assertContains(response, 'test_field_2')
    
    def test_fields_data_structure(self):
        """Test that fields_data is structured correctly for JavaScript"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        # Extract the fields data from the response
        content = response.content.decode()
        
        # Find the JSON script tag
        import re
        json_match = re.search(r'<script[^>]*id="allFields"[^>]*>(.*?)</script>', content, re.DOTALL)
        self.assertIsNotNone(json_match, "allFields script tag not found")
        
        fields_json = json_match.group(1).strip()
        fields_data = json.loads(fields_json)
        
        # Verify the structure
        self.assertIsInstance(fields_data, list)
        self.assertGreaterEqual(len(fields_data), 2)
        
        # Check first field
        field1_data = next(f for f in fields_data if f['field_name'] == 'test_field_1')
        self.assertEqual(field1_data['field_name'], 'test_field_1')
        self.assertEqual(field1_data['label'], 'Test Field 1')
        self.assertEqual(field1_data['field_type'], 'text')
        self.assertTrue(field1_data['enabled'])
        self.assertTrue(field1_data['required'])
        self.assertEqual(field1_data['order'], 1)
        
        # Check second field
        field2_data = next(f for f in fields_data if f['field_name'] == 'test_field_2')
        self.assertEqual(field2_data['field_name'], 'test_field_2')
        self.assertEqual(field2_data['label'], 'Test Field 2')
        self.assertEqual(field2_data['field_type'], 'choice')
        self.assertTrue(field2_data['enabled'])
        self.assertFalse(field2_data['required'])
        self.assertEqual(field2_data['order'], 2)
        self.assertEqual(field2_data['choices'], 'Option A,Option B,Option C')
    
    def test_geometry_details_api_returns_correct_data(self):
        """Test that the geometry details API returns the correct structure"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('geometry_details', kwargs={'geometry_id': self.geometry.id}))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('geometry', data)
        
        geometry_data = data['geometry']
        self.assertEqual(geometry_data['id'], self.geometry.id)
        self.assertEqual(geometry_data['id_kurz'], 'TEST001')
        self.assertIn('entries', geometry_data)
        
        # Check entries structure
        entries = geometry_data['entries']
        self.assertEqual(len(entries), 1)
        
        entry = entries[0]
        self.assertEqual(entry['id'], self.entry.id)
        self.assertEqual(entry['name'], 'Test Entry')
        self.assertEqual(entry['year'], 2023)
        
        # Check that field values are included
        self.assertIn('test_field_1', entry)
        self.assertEqual(entry['test_field_1'], 'Test Value 1')
        self.assertIn('test_field_2', entry)
        self.assertEqual(entry['test_field_2'], 'Option A')
    
    def test_geometry_details_api_with_no_entries(self):
        """Test geometry details API when there are no entries"""
        # Create a geometry without entries
        from django.contrib.gis.geos import Point
        empty_geometry = DataGeometry.objects.create(
            dataset=self.dataset,
            id_kurz='EMPTY001',
            address='Empty Address',
            geometry=Point(16.0, 49.0),
            user=self.user
        )
        
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('geometry_details', kwargs={'geometry_id': empty_geometry.id}))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        
        geometry_data = data['geometry']
        self.assertEqual(geometry_data['id'], empty_geometry.id)
        self.assertEqual(geometry_data['id_kurz'], 'EMPTY001')
        self.assertEqual(len(geometry_data['entries']), 0)
    
    def test_geometry_details_api_with_disabled_fields(self):
        """Test that disabled fields are not included in the API response"""
        # Disable one field
        self.field2.enabled = False
        self.field2.save()
        
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('geometry_details', kwargs={'geometry_id': self.geometry.id}))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        geometry_data = data['geometry']
        entries = geometry_data['entries']
        
        # Check that only enabled fields are included
        entry = entries[0]
        self.assertIn('test_field_1', entry)  # Enabled field
        self.assertNotIn('test_field_2', entry)  # Disabled field
    
    def test_map_data_api_returns_lightweight_data(self):
        """Test that the map data API returns lightweight data without field details"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_map_data', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('map_data', data)
        
        map_data = data['map_data']
        self.assertEqual(len(map_data), 1)
        
        point = map_data[0]
        self.assertEqual(point['id'], self.geometry.id)
        self.assertEqual(point['id_kurz'], 'TEST001')
        self.assertEqual(point['address'], 'Test Address')
        self.assertIn('lat', point)
        self.assertIn('lng', point)
        self.assertIn('user', point)
        
        # Should not contain entries or field data
        self.assertNotIn('entries', point)
    
    def test_javascript_template_variables(self):
        """Test that JavaScript template variables are set correctly"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check that allowMultipleEntries is set
        self.assertIn('window.allowMultipleEntries', content)
        
        # Check that translations are set
        self.assertIn('window.translations', content)
        
        # Check that the initializeDataInput function is called
        self.assertIn('initializeDataInput', content)
    
    def test_no_fields_configured_scenario(self):
        """Test the scenario when no fields are configured"""
        # Remove all fields
        DatasetField.objects.filter(dataset=self.dataset).delete()
        
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check that allFields is empty
        json_match = re.search(r'<script[^>]*id="allFields"[^>]*>(.*?)</script>', content, re.DOTALL)
        self.assertIsNotNone(json_match)
        
        fields_json = json_match.group(1).strip()
        fields_data = json.loads(fields_json)
        self.assertGreaterEqual(len(fields_data), 8)
    
    def test_javascript_file_loading(self):
        """Test that the external JavaScript file is loaded correctly"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check that the external JavaScript file is referenced
        self.assertIn('/static/js/data-input.js', content, "External JavaScript file not referenced")
        
        # Read the JavaScript file directly from the filesystem
        import os
        from django.conf import settings
        
        js_file_path = os.path.join(settings.STATIC_ROOT, 'js', 'data-input.js')
        if not os.path.exists(js_file_path):
            js_file_path = os.path.join(settings.STATICFILES_DIRS[0], 'js', 'data-input.js')
        
        self.assertTrue(os.path.exists(js_file_path), f"JavaScript file not found at {js_file_path}")
        
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check that key JavaScript functions are defined in the external file
        required_functions = [
            'function generateEntriesTable',
            'function showGeometryDetails',
            'function selectPoint',
            'function loadGeometryDetails',
            'function createFormFieldInput',
            'function initializeDataInput'
        ]
        
        for func in required_functions:
            self.assertIn(func, js_content, f"Function {func} not found in external JavaScript file")
    
    def test_javascript_debug_logging_present(self):
        """Test that debug logging is present in the external JavaScript file"""
        # Read the JavaScript file directly from the filesystem
        import os
        from django.conf import settings
        
        js_file_path = os.path.join(settings.STATIC_ROOT, 'js', 'data-input.js')
        if not os.path.exists(js_file_path):
            js_file_path = os.path.join(settings.STATICFILES_DIRS[0], 'js', 'data-input.js')
        
        self.assertTrue(os.path.exists(js_file_path), f"JavaScript file not found at {js_file_path}")
        
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check that debug logging is present in the external file
        debug_statements = [
            'console.log(\'generateEntriesTable called with point:\'',
            'console.log(\'window.allFields:\'',
            'console.log(\'New entry form - Checking window.allFields:\'',
            'console.log(\'New entry form - Has enabled fields:\'',
            'console.log(\'New entry form - Rendering field:\''
        ]
        
        for debug_stmt in debug_statements:
            self.assertIn(debug_stmt, js_content, f"Debug statement {debug_stmt} not found in external JavaScript file")
    
    def test_geometry_details_api_structure_matches_js_expectations(self):
        """Test that the API response structure matches what JavaScript expects"""
        client = Client()
        client.force_login(self.user)
        
        # Test the geometry details API
        response = client.get(reverse('geometry_details', kwargs={'geometry_id': self.geometry.id}))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        # Verify the structure that JavaScript expects
        self.assertIn('success', data)
        self.assertTrue(data['success'])
        self.assertIn('geometry', data)
        
        geometry = data['geometry']
        required_fields = ['id', 'id_kurz', 'address', 'lat', 'lng', 'user', 'entries']
        for field in required_fields:
            self.assertIn(field, geometry, f"Required field {field} missing from geometry data")
        
        # Check entries structure
        entries = geometry['entries']
        self.assertIsInstance(entries, list)
        
        if entries:
            entry = entries[0]
            entry_required_fields = ['id', 'name', 'year', 'user']
            for field in entry_required_fields:
                self.assertIn(field, entry, f"Required field {field} missing from entry data")
    
    def test_template_renders_with_correct_context(self):
        """Test that the template receives the correct context variables"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        # Check that the template context contains the expected variables
        self.assertIn('dataset', response.context)
        self.assertIn('fields_data', response.context)
        self.assertIn('allow_multiple_entries', response.context)
        
        # Verify the context values
        self.assertEqual(response.context['dataset'], self.dataset)
        self.assertIsInstance(response.context['fields_data'], list)
        self.assertGreaterEqual(len(response.context['fields_data']), 2)
        context_field_names = {field['field_name'] for field in response.context['fields_data']}
        self.assertIn('test_field_1', context_field_names)
        self.assertIn('test_field_2', context_field_names)
        self.assertIsInstance(response.context['allow_multiple_entries'], bool)
