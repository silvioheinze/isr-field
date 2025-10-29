from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
import json

from ..models import DataSet, DataGeometry, DataEntry, DataEntryField, DatasetField


class JavaScriptConsoleOutputTestCase(TestCase):
    """Test to simulate the JavaScript console output issue"""
    
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
    
    def test_simulate_javascript_execution(self):
        """Simulate the JavaScript execution to find the issue"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Extract the allFields JSON
        import re
        json_match = re.search(r'<script[^>]*id="allFields"[^>]*>(.*?)</script>', content, re.DOTALL)
        self.assertIsNotNone(json_match, "allFields script tag not found")
        
        fields_json = json_match.group(1).strip()
        fields_data = json.loads(fields_json)
        
        print(f"\n=== JavaScript Simulation ===")
        print(f"Fields JSON: {fields_json}")
        print(f"Parsed fields_data: {fields_data}")
        print(f"Number of fields: {len(fields_data)}")
        
        # Simulate the JavaScript initialization
        print(f"\n=== Simulating JavaScript Initialization ===")
        
        # Simulate: var allFieldsElement = document.getElementById('allFields');
        allFieldsElement = {'textContent': fields_json}
        
        # Simulate: if (allFieldsElement && allFieldsElement.textContent) {
        if allFieldsElement and allFieldsElement['textContent']:
            # Simulate: window.allFields = JSON.parse(allFieldsElement.textContent);
            window_allFields = json.loads(allFieldsElement['textContent'])
            print(f"window.allFields initialized: {window_allFields}")
        else:
            print("allFields element not found or empty")
            window_allFields = []
        
        # Check if window.allFields is empty
        if not window_allFields:
            print("❌ PROBLEM: window.allFields is empty!")
        else:
            print(f"✅ window.allFields has {len(window_allFields)} fields")
            for field in window_allFields:
                print(f"  - {field['field_name']}: {field['label']} (enabled: {field['enabled']})")
        
        # Simulate the generateEntriesTable function call
        print(f"\n=== Simulating generateEntriesTable Function ===")
        
        # Simulate a point with entries
        test_point = {
            'id': 1,
            'id_kurz': 'TEST001',
            'address': 'Test Address',
            'entries': [
                {
                    'id': 1,
                    'name': 'Test Entry',
                    'year': 2023,
                    'test_field_1': 'Test Value 1',
                    'test_field_2': 'Option A'
                }
            ]
        }
        
        print(f"Test point: {test_point}")
        print(f"window.allFields: {window_allFields}")
        
        # Simulate the field rendering logic
        if window_allFields and len(window_allFields) > 0:
            print("✅ Fields available for rendering")
            
            # Check if there are any enabled fields
            enabled_fields = [field for field in window_allFields if field.get('enabled', False)]
            print(f"Enabled fields: {len(enabled_fields)}")
            
            if enabled_fields:
                print("✅ Enabled fields found - should render fields")
                for field in enabled_fields:
                    print(f"  - Rendering field: {field['field_name']}")
            else:
                print("❌ No enabled fields found - will show 'No fields configured' message")
        else:
            print("❌ No fields available - will show 'No fields configured' message")
    
    def test_check_actual_dataset_fields(self):
        """Check what fields exist in the actual dataset"""
        # First, let's see what datasets exist
        datasets = DataSet.objects.all()
        print(f"\n=== Available Datasets ===")
        for dataset in datasets:
            print(f"Dataset {dataset.id}: {dataset.name}")
            
            # Get fields for this dataset
            fields = DatasetField.objects.filter(dataset=dataset)
            print(f"  Fields: {fields.count()}")
            for field in fields:
                print(f"    - {field.field_name}: {field.label} (enabled: {field.enabled})")
        
        # If we have datasets, test with the first one
        if datasets.exists():
            dataset = datasets.first()
            print(f"\n=== Testing with Dataset {dataset.id} ===")
            
            client = Client()
            client.force_login(self.user)
            
            response = client.get(reverse('dataset_data_input', kwargs={'dataset_id': dataset.id}))
            if response.status_code == 200:
                content = response.content.decode()
                
                # Extract the allFields JSON
                import re
                json_match = re.search(r'<script[^>]*id="allFields"[^>]*>(.*?)</script>', content, re.DOTALL)
                if json_match:
                    fields_json = json_match.group(1).strip()
                    if fields_json:
                        fields_data = json.loads(fields_json)
                        print(f"Fields in template: {len(fields_data)}")
                        for field in fields_data:
                            print(f"  - {field['field_name']}: {field['label']} (enabled: {field['enabled']})")
                    else:
                        print("Empty fields JSON in template!")
                else:
                    print("No allFields script tag found!")
            else:
                print(f"Could not access dataset: {response.status_code}")
