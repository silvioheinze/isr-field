from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from ..models import DataSet, DatasetFieldConfig, DataGeometry, DataEntry, DataEntryField, Typology, TypologyEntry, DatasetField
from ..views import DatasetFieldConfigForm, DatasetFieldForm, GroupForm


class CSVDelimiterDetectionTest(TestCase):
    """Tests for CSV delimiter detection functionality"""
    
    def test_detect_comma_delimiter(self):
        """Test detection of comma-separated CSV files"""
        csv_content = """ID,Name,Address,Latitude,Longitude
1,Test Building,Street 1,48.123,16.456
2,Another Building,Street 2,48.124,16.457
3,Third Building,Street 3,48.125,16.458"""
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        self.assertEqual(delimiter, ',')
    
    def test_detect_semicolon_delimiter(self):
        """Test detection of semicolon-separated CSV files (European format)"""
        csv_content = """ID;Name;Address;Latitude;Longitude
1;Test Building;Street 1;48.123;16.456
2;Another Building;Street 2;48.124;16.457
3;Third Building;Street 3;48.125;16.458"""
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        self.assertEqual(delimiter, ';')
    
    def test_detect_tab_delimiter(self):
        """Test detection of tab-separated CSV files"""
        csv_content = """ID	Name	Address	Latitude	Longitude
1	Test Building	Street 1	48.123	16.456
2	Another Building	Street 2	48.124	16.457
3	Third Building	Street 3	48.125	16.458"""
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        self.assertEqual(delimiter, '\t')
    
    def test_detect_pipe_delimiter(self):
        """Test detection of pipe-separated CSV files"""
        csv_content = """ID|Name|Address|Latitude|Longitude
1|Test Building|Street 1|48.123|16.456
2|Another Building|Street 2|48.124|16.457
3|Third Building|Street 3|48.125|16.458"""
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        self.assertEqual(delimiter, '|')
    
    def test_detect_delimiter_with_quoted_fields(self):
        """Test detection with quoted fields containing commas"""
        csv_content = """ID,Name,Address,Description,Latitude,Longitude
1,"Test Building","Street 1, Vienna","A nice building, with garden",48.123,16.456
2,"Another Building","Street 2, Vienna","Another building, with pool",48.124,16.457"""
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        self.assertEqual(delimiter, ',')
    
    def test_detect_delimiter_with_mixed_content(self):
        """Test detection with mixed content and special characters"""
        csv_content = """ID;Name;Address;Value;Date
1;Test Building;Street 1;€1,234.56;2023-01-01
2;Another Building;Street 2;€2,345.67;2023-01-02
3;Third Building;Street 3;€3,456.78;2023-01-03"""
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        self.assertEqual(delimiter, ';')
    
    def test_detect_delimiter_empty_content(self):
        """Test detection with empty content"""
        csv_content = ""
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        self.assertEqual(delimiter, ',')  # Should default to comma
    
    def test_detect_delimiter_single_line(self):
        """Test detection with single line content"""
        csv_content = "ID,Name,Address,Latitude,Longitude"
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        self.assertEqual(delimiter, ',')
    
    def test_detect_delimiter_whitespace_lines(self):
        """Test detection with whitespace-only lines"""
        csv_content = """ID,Name,Address,Latitude,Longitude
        
1,Test Building,Street 1,48.123,16.456
        
2,Another Building,Street 2,48.124,16.457
"""
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        self.assertEqual(delimiter, ',')
    
    def test_detect_delimiter_inconsistent_columns(self):
        """Test detection with inconsistent number of columns"""
        csv_content = """ID,Name,Address,Latitude,Longitude
1,Test Building,Street 1,48.123,16.456
2,Another Building,Street 2,48.124,16.457,Extra
3,Third Building,Street 3,48.125,16.458"""
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        # Should still detect comma as the most common delimiter
        self.assertEqual(delimiter, ',')
    
    def test_detect_delimiter_semicolon_vs_comma(self):
        """Test detection when both semicolon and comma are present"""
        csv_content = """ID;Name;Address;Description,Latitude;Longitude
1;Test Building;Street 1;"A nice building, with garden";48.123;16.456
2;Another Building;Street 2;"Another building, with pool";48.124;16.457"""
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        # Should prefer semicolon as it's more consistent
        self.assertEqual(delimiter, ';')
    
    def test_detect_delimiter_small_sample(self):
        """Test detection with very small sample size"""
        csv_content = "ID,Name,Address"
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content, sample_size=10)
        self.assertEqual(delimiter, ',')
    
    def test_detect_delimiter_large_file(self):
        """Test detection with large file (should only analyze first part)"""
        # Create a large CSV content
        header = "ID,Name,Address,Latitude,Longitude"
        rows = [f"{i},Building {i},Street {i},48.12{i},16.45{i}" for i in range(1, 1000)]
        csv_content = header + "\n" + "\n".join(rows)
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content, sample_size=1024)
        self.assertEqual(delimiter, ',')
    
    def test_detect_delimiter_no_clear_delimiter(self):
        """Test detection when no clear delimiter is found"""
        csv_content = "This is just some text without clear delimiters"
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        self.assertEqual(delimiter, ',')  # Should default to comma
    
    def test_detect_delimiter_single_column(self):
        """Test detection with single column (no delimiters)"""
        csv_content = """ID
1
2
3"""
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        self.assertEqual(delimiter, ',')  # Should default to comma
    
    def test_detect_delimiter_unicode_content(self):
        """Test detection with unicode content"""
        csv_content = """ID;Name;Address;Latitude;Longitude
1;Test Gebäude;Straße 1;48.123;16.456
2;Another Gebäude;Straße 2;48.124;16.457
3;Third Gebäude;Straße 3;48.125;16.458"""
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        self.assertEqual(delimiter, ';')
    
    def test_detect_delimiter_numeric_data(self):
        """Test detection with primarily numeric data"""
        csv_content = """1,2,3,4,5
10,20,30,40,50
100,200,300,400,500
1000,2000,3000,4000,5000"""
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        self.assertEqual(delimiter, ',')
    
    def test_detect_delimiter_mixed_delimiters_score(self):
        """Test that the scoring algorithm works correctly with mixed delimiters"""
        # This content has more semicolons than commas, so semicolon should win
        csv_content = """ID;Name;Address;Value;Date;Status
1;Test Building;Street 1;1000;2023-01-01;Active
2;Another Building;Street 2;2000;2023-01-02;Inactive
3;Third Building;Street 3;3000;2023-01-03;Active"""
        
        from ..views import detect_csv_delimiter
        delimiter = detect_csv_delimiter(csv_content)
        self.assertEqual(delimiter, ';')
