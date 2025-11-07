from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
import json

from ..models import DataSet, DataGeometry, DataEntry, DataEntryField, DatasetField


class WindowAllFieldsDebugTestCase(TestCase):
    """Debug test to check window.allFields initialization"""
    
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
    
    def test_window_allfields_initialization_timing(self):
        """Test that window.allFields is initialized before initializeDataInput is called"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check that the initialization code is present
        self.assertIn('window.allFields = JSON.parse(allFieldsElement.textContent);', content)
        self.assertIn('console.log(\'window.allFields initialized:\', window.allFields);', content)
        
        # Check that the allFields script tag exists and has content
        import re
        json_match = re.search(r'<script[^>]*id="allFields"[^>]*>(.*?)</script>', content, re.DOTALL)
        self.assertIsNotNone(json_match, "allFields script tag not found")
        
        fields_json = json_match.group(1).strip()
        fields_data = json.loads(fields_json)
        
        # Should include our custom field among the standard ones
        field_names = {field['field_name'] for field in fields_data}
        self.assertIn('test_field_1', field_names)
        
        # Check that the initialization happens before initializeDataInput
        init_index = content.find('window.allFields = JSON.parse(allFieldsElement.textContent);')
        initialize_index = content.find('initializeDataInput(typologyData, allFields);')
        
        self.assertGreater(init_index, 0, "window.allFields initialization not found")
        self.assertGreater(initialize_index, 0, "initializeDataInput call not found")
        self.assertLess(init_index, initialize_index, "window.allFields initialization should happen before initializeDataInput call")
    
    def test_actual_dataset_with_fields(self):
        """Test with the actual dataset that has the issue"""
        # This test simulates the real scenario
        client = Client()
        client.force_login(self.user)
        
        # Access the actual dataset (assuming dataset ID 4 exists)
        response = client.get('/datasets/4/data-input/')
        
        if response.status_code == 200:
            content = response.content.decode()
            
            # Check if allFields script tag exists
            import re
            json_match = re.search(r'<script[^>]*id="allFields"[^>]*>(.*?)</script>', content, re.DOTALL)
            
            if json_match:
                fields_json = json_match.group(1).strip()
                print(f"Actual dataset fields JSON: {fields_json}")
                
                if fields_json:
                    try:
                        fields_data = json.loads(fields_json)
                        print(f"Parsed fields_data: {fields_data}")
                        print(f"Number of fields: {len(fields_data)}")
                        
                        if len(fields_data) > 0:
                            print("Fields found in actual dataset!")
                            for field in fields_data:
                                print(f"  - {field['field_name']}: {field['label']} (enabled: {field['enabled']})")
                        else:
                            print("No fields found in actual dataset!")
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                else:
                    print("Empty fields JSON in actual dataset!")
            else:
                print("No allFields script tag found in actual dataset!")
        else:
            print(f"Could not access dataset 4: {response.status_code}")
            # Just test that the template renders correctly
            response = client.get(reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id}))
            self.assertEqual(response.status_code, 200)
