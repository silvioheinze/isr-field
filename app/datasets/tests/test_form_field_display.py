from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.urls import reverse
from ..models import DataSet, DataGeometry, DataEntry, DataEntryField, DatasetField


class FormFieldDisplayTest(TestCase):
    """Test cases for form field display in data input template"""
    
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
        
        # Create a geometry point
        self.geometry = DataGeometry.objects.create(
            dataset=self.dataset,
            geometry=Point(16.0, 48.0),
            id_kurz='TEST001',
            address='Test Address',
            user=self.user
        )
        
        # Create test entry
        self.entry = DataEntry.objects.create(
            geometry=self.geometry,
            name='Test Entry',
            year=2023,
            user=self.user
        )
    
    def test_no_fields_configured(self):
        """Test when no fields are configured - should have empty fields array"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('dataset_data_input', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        
        # Check that window.allFields is empty (no fields configured)
        self.assertContains(response, 'window.allFields = JSON.parse(document.getElementById')
        self.assertContains(response, '[]')
    
    def test_fields_configured_but_disabled(self):
        """Test when fields exist but are disabled - should have empty fields array"""
        # Create disabled fields
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='disabled_field',
            label='Disabled Field',
            field_type='text',
            enabled=False,  # Disabled
            order=1
        )
        
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='another_disabled_field',
            label='Another Disabled Field',
            field_type='integer',
            enabled=False,  # Disabled
            order=2
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('dataset_data_input', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        
        # Check that window.allFields is empty (no enabled fields)
        self.assertContains(response, 'window.allFields = JSON.parse(document.getElementById')
        self.assertContains(response, '[]')
    
    def test_fields_configured_and_enabled(self):
        """Test when fields exist and are enabled - should show form fields"""
        # Create enabled fields
        field1 = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='enabled_field',
            label='Enabled Field',
            field_type='text',
            enabled=True,  # Enabled
            order=1
        )
        
        field2 = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='another_enabled_field',
            label='Another Enabled Field',
            field_type='integer',
            enabled=True,  # Enabled
            order=2
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('dataset_data_input', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        
        # Check that the template does NOT contain the no fields message
        self.assertNotContains(response, 'No fields configured for this dataset')
        
        # Check that window.allFields contains the enabled fields
        self.assertContains(response, 'window.allFields = JSON.parse(document.getElementById')
        self.assertContains(response, 'enabled_field')
        self.assertContains(response, 'another_enabled_field')
    
    def test_mixed_enabled_disabled_fields(self):
        """Test when some fields are enabled and some are disabled - should only show enabled fields"""
        # Create disabled field
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='disabled_field',
            label='Disabled Field',
            field_type='text',
            enabled=False,  # Disabled
            order=1
        )
        
        # Create enabled field
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='enabled_field',
            label='Enabled Field',
            field_type='text',
            enabled=True,  # Enabled
            order=2
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('dataset_data_input', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        
        # Check that the template does NOT contain the no fields message
        self.assertNotContains(response, 'No fields configured for this dataset')
        
        # Check that window.allFields contains only the enabled field
        self.assertContains(response, 'window.allFields = JSON.parse(document.getElementById')
        self.assertContains(response, 'enabled_field')
        self.assertNotContains(response, 'disabled_field')
    
    def test_fields_with_data_but_disabled(self):
        """Test when fields have data but are disabled - should have empty fields array"""
        # Create disabled field
        disabled_field = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='disabled_field',
            label='Disabled Field',
            field_type='text',
            enabled=False,  # Disabled
            order=1
        )
        
        # Create field data for the disabled field
        DataEntryField.objects.create(
            entry=self.entry,
            field_name='disabled_field',
            value='Some data'
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('dataset_data_input', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        
        # Check that window.allFields is empty (no enabled fields)
        self.assertContains(response, 'window.allFields = JSON.parse(document.getElementById')
        self.assertContains(response, '[]')
    
    def test_fields_with_typology_choices(self):
        """Test fields with typology choices are properly included"""
        from ..models import Typology, TypologyEntry
        
        # Create typology
        typology = Typology.objects.create(
            name='Test Typology'
        )
        
        # Create typology entries
        TypologyEntry.objects.create(
            typology=typology,
            code=1,
            category='Test Category',
            name='Option 1'
        )
        TypologyEntry.objects.create(
            typology=typology,
            code=2,
            category='Test Category',
            name='Option 2'
        )
        
        # Create field with typology
        field = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='typology_field',
            label='Typology Field',
            field_type='choice',
            enabled=True,
            order=1,
            typology=typology
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('dataset_data_input', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        
        # Check that the template does NOT contain the no fields message
        self.assertNotContains(response, 'No fields configured for this dataset')
        
        # Check that window.allFields contains the typology field
        self.assertContains(response, 'window.allFields = JSON.parse(document.getElementById')
        self.assertContains(response, 'typology_field')
    
    def test_fields_ordering(self):
        """Test that fields are displayed in the correct order"""
        # Create fields with different orders
        field3 = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='field_c',
            label='Field C',
            field_type='text',
            enabled=True,
            order=3
        )
        
        field1 = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='field_a',
            label='Field A',
            field_type='text',
            enabled=True,
            order=1
        )
        
        field2 = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='field_b',
            label='Field B',
            field_type='text',
            enabled=True,
            order=2
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('dataset_data_input', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        
        # Check that the template does NOT contain the no fields message
        self.assertNotContains(response, 'No fields configured for this dataset')
        
        # Check that window.allFields contains all fields
        self.assertContains(response, 'window.allFields = JSON.parse(document.getElementById')
        self.assertContains(response, 'field_a')
        self.assertContains(response, 'field_b')
        self.assertContains(response, 'field_c')
    
    def test_dataset_with_allow_multiple_entries_false(self):
        """Test dataset with allow_multiple_entries=False"""
        # Update dataset to not allow multiple entries
        self.dataset.allow_multiple_entries = False
        self.dataset.save()
        
        # Create enabled field
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='single_entry_field',
            label='Single Entry Field',
            field_type='text',
            enabled=True,
            order=1
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('dataset_data_input', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        
        # Check that the template does NOT contain the no fields message
        self.assertNotContains(response, 'No fields configured for this dataset')
        
        # Check that window.allFields contains the field
        self.assertContains(response, 'window.allFields = JSON.parse(document.getElementById')
        self.assertContains(response, 'single_entry_field')
    
    def test_dataset_with_allow_multiple_entries_true(self):
        """Test dataset with allow_multiple_entries=True"""
        # Update dataset to allow multiple entries
        self.dataset.allow_multiple_entries = True
        self.dataset.save()
        
        # Create enabled field
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='multiple_entry_field',
            label='Multiple Entry Field',
            field_type='text',
            enabled=True,
            order=1
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('dataset_data_input', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        
        # Check that the template does NOT contain the no fields message
        self.assertNotContains(response, 'No fields configured for this dataset')
        
        # Check that window.allFields contains the field
        self.assertContains(response, 'window.allFields = JSON.parse(document.getElementById')
        self.assertContains(response, 'multiple_entry_field')
    
    def test_debug_field_configuration_data(self):
        """Test to debug what field configuration data is being passed to the template"""
        # Create various field configurations
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='text_field',
            label='Text Field',
            field_type='text',
            enabled=True,
            order=1,
            required=True,
            help_text='This is a text field'
        )
        
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='disabled_text_field',
            label='Disabled Text Field',
            field_type='text',
            enabled=False,
            order=2
        )
        
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='integer_field',
            label='Integer Field',
            field_type='integer',
            enabled=True,
            order=3,
            required=False,
            help_text='Enter a number between 0 and 100'
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('dataset_data_input', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        
        # Debug: Print the response content to see what's being passed
        print("\n=== DEBUG: Response Content ===")
        print(response.content.decode('utf-8'))
        print("=== END DEBUG ===\n")
        
        # Check that the template does NOT contain the no fields message
        self.assertNotContains(response, 'No fields configured for this dataset')
        
        # Check that window.allFields contains the enabled fields
        self.assertContains(response, 'window.allFields = JSON.parse(document.getElementById')
        self.assertContains(response, 'text_field')
        self.assertContains(response, 'integer_field')
        self.assertNotContains(response, 'disabled_text_field')
