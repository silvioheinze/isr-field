from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.gis.geos import Point
import io
import csv

from ..models import DataSet, DataGeometry, DataEntry, DataEntryField, DatasetField


class CSVImportTestCase(TestCase):
    """Test CSV import functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.dataset = DataSet.objects.create(
            name='Test Dataset',
            description='Test dataset for import',
            owner=self.user
        )
    
    def test_csv_import_view_get(self):
        """Test GET request to CSV import view"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_csv_import', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Import CSV Data')
        self.assertContains(response, 'Select CSV File')
    
    def test_csv_import_view_post_no_file(self):
        """Test POST request to CSV import view without file"""
        client = Client()
        client.force_login(self.user)
        
        response = client.post(reverse('dataset_csv_import', args=[self.dataset.id]), {})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please select a CSV file')
    
    def test_csv_import_view_post_with_file(self):
        """Test POST request to CSV import view with valid CSV file"""
        client = Client()
        client.force_login(self.user)
        
        # Create a test CSV file
        csv_content = """ID,ADRESSE,GEB_X,GEB_Y,2016_NUTZUNG,2016_CAT_INNO
test_001,Test Address 1,656610,3399131,870,999
test_002,Test Address 2,656620,3399141,640,0"""
        
        csv_file = SimpleUploadedFile(
            "test.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )
        
        response = client.post(
            reverse('dataset_csv_import', args=[self.dataset.id]),
            {'csv_file': csv_file}
        )
        
        # Should redirect to column selection
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dataset_csv_column_selection', args=[self.dataset.id]))
    
    def test_csv_column_selection_view_get(self):
        """Test GET request to CSV column selection view"""
        client = Client()
        client.force_login(self.user)
        
        # Set up session data
        session = client.session
        session['csv_data'] = """ID,ADRESSE,GEB_X,GEB_Y,2016_NUTZUNG
test_001,Test Address 1,656610,3399131,870
test_002,Test Address 2,656620,3399141,640"""
        session['csv_delimiter'] = ','
        session.save()
        
        response = client.get(reverse('dataset_csv_column_selection', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Column Selection')
        
        # Check that columns are displayed
        content = response.content.decode('utf-8')
        self.assertIn('ID', content)
        self.assertIn('ADRESSE', content)
        self.assertIn('GEB_X', content)
        self.assertIn('GEB_Y', content)
        self.assertIn('2016_NUTZUNG', content)
    
    def test_csv_column_selection_view_post_missing_data(self):
        """Test POST request to CSV column selection view with missing data"""
        client = Client()
        client.force_login(self.user)
        
        # Set up session data
        session = client.session
        session['csv_data'] = """ID,ADRESSE,GEB_X,GEB_Y,2016_NUTZUNG
test_001,Test Address 1,656610,3399131,870
test_002,Test Address 2,656620,3399141,640"""
        session['csv_delimiter'] = ','
        session.save()
        
        response = client.post(
            reverse('dataset_csv_column_selection', args=[self.dataset.id]),
            {'id_column': 'ID'}  # Missing coordinate_system
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please select an ID column and coordinate system')
    
    def test_csv_column_selection_view_post_valid_data(self):
        """Test POST request to CSV column selection view with valid data"""
        client = Client()
        client.force_login(self.user)
        
        # Set up session data
        session = client.session
        session['csv_data'] = """ID,ADRESSE,GEB_X,GEB_Y,2016_NUTZUNG,2016_CAT_INNO
test_001,Test Address 1,656610,3399131,870,999
test_002,Test Address 2,656620,3399141,640,0"""
        session['csv_delimiter'] = ','
        session.save()
        
        response = client.post(
            reverse('dataset_csv_column_selection', args=[self.dataset.id]),
            {
                'id_column': 'ID',
                'coordinate_system': '4326',
                'x_column': 'GEB_X',
                'y_column': 'GEB_Y'
            }
        )
        
        # Should redirect to dataset detail
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dataset_detail', args=[self.dataset.id]))
    
    def test_csv_import_creates_geometries(self):
        """Test that CSV import creates geometries correctly"""
        client = Client()
        client.force_login(self.user)
        
        # Set up session data
        session = client.session
        session['csv_data'] = """ID,ADRESSE,GEB_X,GEB_Y,2016_NUTZUNG,2016_CAT_INNO
test_001,Test Address 1,656610,3399131,870,999
test_002,Test Address 2,656620,3399141,640,0"""
        session['csv_delimiter'] = ','
        session.save()
        
        # Check initial state
        self.assertEqual(DataGeometry.objects.filter(dataset=self.dataset).count(), 0)
        self.assertEqual(DataEntry.objects.filter(geometry__dataset=self.dataset).count(), 0)
        
        # Perform import
        response = client.post(
            reverse('dataset_csv_column_selection', args=[self.dataset.id]),
            {
                'id_column': 'ID',
                'coordinate_system': '4326',
                'x_column': 'GEB_X',
                'y_column': 'GEB_Y'
            }
        )
        
        # Check that geometries were created
        self.assertEqual(DataGeometry.objects.filter(dataset=self.dataset).count(), 2)
        self.assertEqual(DataEntry.objects.filter(geometry__dataset=self.dataset).count(), 2)
        
        # Check specific geometry
        geometry = DataGeometry.objects.get(dataset=self.dataset, id_kurz='test_001')
        self.assertEqual(geometry.address, 'Unknown Address (test_001)')
        self.assertEqual(geometry.user, self.user)
        
        # Check entry
        entry = DataEntry.objects.get(geometry=geometry)
        self.assertEqual(entry.name, 'test_001')
        self.assertEqual(entry.user, self.user)
    
    def test_csv_import_creates_field_values(self):
        """Test that CSV import creates field values correctly"""
        client = Client()
        client.force_login(self.user)
        
        # Set up session data
        session = client.session
        session['csv_data'] = """ID,ADRESSE,GEB_X,GEB_Y,2016_NUTZUNG,2016_CAT_INNO
test_001,Test Address 1,656610,3399131,870,999
test_002,Test Address 2,656620,3399141,640,0"""
        session['csv_delimiter'] = ','
        session.save()
        
        # Perform import
        response = client.post(
            reverse('dataset_csv_column_selection', args=[self.dataset.id]),
            {
                'id_column': 'ID',
                'coordinate_system': '4326',
                'x_column': 'GEB_X',
                'y_column': 'GEB_Y'
            }
        )
        
        # Check that dataset fields were created
        # Should have 3 fields: 2016_NUTZUNG, 2016_CAT_INNO, and ADRESSE
        self.assertEqual(DatasetField.objects.filter(dataset=self.dataset).count(), 3)
        
        # Check specific field
        field = DatasetField.objects.get(dataset=self.dataset, field_name='2016_NUTZUNG')
        self.assertEqual(field.label, '2016_NUTZUNG')
        self.assertEqual(field.field_type, 'text')
        self.assertTrue(field.enabled)
        
        # Check that entry fields were created
        geometry = DataGeometry.objects.get(dataset=self.dataset, id_kurz='test_001')
        entry = DataEntry.objects.get(geometry=geometry)
        
        # Should have 3 entry fields: 2016_NUTZUNG, 2016_CAT_INNO, and ADRESSE
        self.assertEqual(DataEntryField.objects.filter(entry=entry).count(), 3)
        
        # Check specific field value
        field_value = DataEntryField.objects.get(entry=entry, field_name='2016_NUTZUNG')
        self.assertEqual(field_value.value, '870')
    
    def test_csv_import_with_semicolon_delimiter(self):
        """Test CSV import with semicolon delimiter"""
        client = Client()
        client.force_login(self.user)
        
        # Set up session data with semicolon delimiter
        session = client.session
        session['csv_data'] = """ID;ADRESSE;GEB_X;GEB_Y;2016_NUTZUNG;2016_CAT_INNO
test_001;Test Address 1;656610;3399131;870;999
test_002;Test Address 2;656620;3399141;640;0"""
        session['csv_delimiter'] = ';'
        session.save()
        
        # Perform import
        response = client.post(
            reverse('dataset_csv_column_selection', args=[self.dataset.id]),
            {
                'id_column': 'ID',
                'coordinate_system': '4326',
                'x_column': 'GEB_X',
                'y_column': 'GEB_Y'
            }
        )
        
        # Check that geometries were created
        self.assertEqual(DataGeometry.objects.filter(dataset=self.dataset).count(), 2)
        self.assertEqual(DataEntry.objects.filter(geometry__dataset=self.dataset).count(), 2)
    
    def test_csv_import_handles_missing_data(self):
        """Test CSV import handles missing data gracefully"""
        client = Client()
        client.force_login(self.user)
        
        # Set up session data with missing data
        session = client.session
        session['csv_data'] = """ID,ADRESSE,GEB_X,GEB_Y,2016_NUTZUNG
test_001,Test Address 1,656610,3399131,870
test_002,Test Address 2,,3399141,640
test_003,Test Address 3,656630,,900"""
        session['csv_delimiter'] = ','
        session.save()
        
        # Perform import
        response = client.post(
            reverse('dataset_csv_column_selection', args=[self.dataset.id]),
            {
                'id_column': 'ID',
                'coordinate_system': '4326',
                'x_column': 'GEB_X',
                'y_column': 'GEB_Y'
            }
        )
        
        # Should only create one geometry (the valid one)
        self.assertEqual(DataGeometry.objects.filter(dataset=self.dataset).count(), 1)
        self.assertEqual(DataEntry.objects.filter(geometry__dataset=self.dataset).count(), 1)
    
    def test_csv_import_access_control(self):
        """Test that CSV import respects access control"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        client = Client()
        client.force_login(other_user)
        
        # Try to access import for dataset owned by different user
        response = client.get(reverse('dataset_csv_import', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 403)
    
    def test_detect_csv_delimiter_function(self):
        """Test the detect_csv_delimiter function"""
        from ..views.import_views import detect_csv_delimiter
        
        # Test comma delimiter
        csv_content = "ID,Name,Value\n1,Test,100\n2,Test2,200"
        delimiter = detect_csv_delimiter(csv_content.encode('utf-8'))
        self.assertEqual(delimiter, ',')
        
        # Test semicolon delimiter
        csv_content = "ID;Name;Value\n1;Test;100\n2;Test2;200"
        delimiter = detect_csv_delimiter(csv_content.encode('utf-8'))
        self.assertEqual(delimiter, ';')
    
    def test_export_options_view(self):
        """Test export options view"""
        client = Client()
        client.force_login(self.user)
        
        response = client.get(reverse('dataset_export_options', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Export Options')
    
    def test_csv_export_view(self):
        """Test CSV export view"""
        client = Client()
        client.force_login(self.user)
        
        # Create some test data
        geometry = DataGeometry.objects.create(
            dataset=self.dataset,
            id_kurz='test_001',
            address='Test Address',
            geometry=Point(656610, 3399131),
            user=self.user
        )
        
        entry = DataEntry.objects.create(
            geometry=geometry,
            name='test_001',
            user=self.user
        )
        
        DataEntryField.objects.create(
            entry=entry,
            field_name='test_field',
            value='test_value'
        )
        
        response = client.get(reverse('dataset_csv_export', args=[self.dataset.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
        
        # Check CSV content
        content = response.content.decode('utf-8')
        self.assertIn('ID,Address,X,Y,User,Entry_Name,Year,test_field', content)
        self.assertIn('test_001,Test Address,656610.0,3399131.0,testuser,test_001,,test_value', content)
