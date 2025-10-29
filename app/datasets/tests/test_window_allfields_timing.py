from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
import json

from ..models import DataSet, DataGeometry, DataEntry, DataEntryField, DatasetField


class WindowAllFieldsTimingTestCase(TestCase):
    """Test to debug the timing issue with window.allFields initialization"""
    
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
    
    def test_template_script_execution_order(self):
        """Test the order of script execution in the template"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Find the allFields script tag
        import re
        json_match = re.search(r'<script[^>]*id="allFields"[^>]*>(.*?)</script>', content, re.DOTALL)
        self.assertIsNotNone(json_match, "allFields script tag not found")
        
        fields_json = json_match.group(1).strip()
        fields_data = json.loads(fields_json)
        
        print(f"\n=== Template Analysis ===")
        print(f"Fields in allFields script tag: {len(fields_data)}")
        print(f"Fields data: {fields_data}")
        
        # Check if the initialization script is present
        self.assertIn('window.allFields = JSON.parse(allFieldsElement.textContent);', content)
        self.assertIn('console.log(\'window.allFields initialized:\', window.allFields);', content)
        
        # Check if the DOMContentLoaded script is present
        self.assertIn('document.addEventListener(\'DOMContentLoaded\', function() {', content)
        self.assertIn('initializeDataInput(typologyData, allFields);', content)
        
        # Check the order of scripts
        allFields_script_pos = content.find('window.allFields = JSON.parse(allFieldsElement.textContent);')
        domContentLoaded_pos = content.find('document.addEventListener(\'DOMContentLoaded\'')
        
        print(f"allFields initialization position: {allFields_script_pos}")
        print(f"DOMContentLoaded position: {domContentLoaded_pos}")
        
        # The allFields initialization should come before DOMContentLoaded
        self.assertLess(allFields_script_pos, domContentLoaded_pos, 
                       "allFields initialization should come before DOMContentLoaded")
        
        print("✅ Script order is correct")
    
    def test_simulate_browser_execution(self):
        """Simulate what happens in the browser"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_data_input', kwargs={'dataset_id': self.dataset.id}))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Extract the allFields JSON
        import re
        json_match = re.search(r'<script[^>]*id="allFields"[^>]*>(.*?)</script>', content, re.DOTALL)
        fields_json = json_match.group(1).strip()
        fields_data = json.loads(fields_json)
        
        print(f"\n=== Browser Simulation ===")
        
        # Simulate: Page loads, scripts execute in order
        print("1. Page loads, allFields script tag is created")
        print(f"   allFields script content: {fields_json}")
        
        print("2. Template script executes immediately")
        # Simulate the template script execution
        allFieldsElement = {'textContent': fields_json}
        if allFieldsElement and allFieldsElement['textContent']:
            window_allFields = json.loads(allFieldsElement['textContent'])
            print(f"   window.allFields initialized: {window_allFields}")
        else:
            window_allFields = []
            print("   window.allFields set to empty array")
        
        print("3. DOMContentLoaded event fires")
        # Simulate the DOMContentLoaded script
        typologyData = None
        allFields = window_allFields or []
        print(f"   allFields parameter: {allFields}")
        
        # Simulate initializeDataInput
        print("4. initializeDataInput called")
        print(f"   typologyDataParam: {typologyData}")
        print(f"   fieldsData parameter: {allFields}")
        print(f"   window.allFields before setting: {window_allFields}")
        
        # Set both variables
        allFields_global = allFields
        window_allFields = allFields
        
        print(f"   allFields set to: {allFields_global}")
        print(f"   window.allFields set to: {window_allFields}")
        
        # Check if fields are available
        if window_allFields and len(window_allFields) > 0:
            print("✅ Fields are available for rendering")
        else:
            print("❌ No fields available - this is the problem!")
    
    def test_check_actual_dataset_4(self):
        """Check what happens with the actual dataset that has the issue"""
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
        
        # Test with the first available dataset
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
                        print("❌ Empty fields JSON in template!")
                else:
                    print("❌ No allFields script tag found!")
            else:
                print(f"❌ Could not access dataset: {response.status_code}")
