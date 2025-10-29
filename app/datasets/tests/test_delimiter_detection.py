from django.test import TestCase
from ..views.import_views import detect_csv_delimiter


class DelimiterDetectionTestCase(TestCase):
    """Test CSV delimiter detection functionality"""
    
    def test_detect_comma_delimiter(self):
        """Test detection of comma delimiter"""
        csv_content = "ID,Name,Value\n1,Test,100\n2,Test2,200"
        delimiter = detect_csv_delimiter(csv_content.encode('utf-8'))
        self.assertEqual(delimiter, ',')
    
    def test_detect_semicolon_delimiter(self):
        """Test detection of semicolon delimiter"""
        csv_content = "ID;Name;Value\n1;Test;100\n2;Test2;200"
        delimiter = detect_csv_delimiter(csv_content.encode('utf-8'))
        self.assertEqual(delimiter, ';')
    
    def test_detect_tab_delimiter(self):
        """Test detection of tab delimiter"""
        csv_content = "ID\tName\tValue\n1\tTest\t100\n2\tTest2\t200"
        delimiter = detect_csv_delimiter(csv_content.encode('utf-8'))
        self.assertEqual(delimiter, '\t')
    
    def test_detect_pipe_delimiter(self):
        """Test detection of pipe delimiter"""
        csv_content = "ID|Name|Value\n1|Test|100\n2|Test2|200"
        delimiter = detect_csv_delimiter(csv_content.encode('utf-8'))
        self.assertEqual(delimiter, '|')
    
    def test_fallback_to_comma(self):
        """Test fallback to comma when detection fails"""
        # Use a string that doesn't contain common delimiters
        csv_content = "IDNameValue\n1Test100\n2Test2200"
        delimiter = detect_csv_delimiter(csv_content.encode('utf-8'))
        self.assertEqual(delimiter, ',')
    
    def test_handle_unicode_content(self):
        """Test handling of unicode content"""
        csv_content = "ID,Name,Value\n1,Tëst,100\n2,Tëst2,200"
        delimiter = detect_csv_delimiter(csv_content.encode('utf-8'))
        self.assertEqual(delimiter, ',')
    
    def test_handle_empty_content(self):
        """Test handling of empty content"""
        csv_content = ""
        delimiter = detect_csv_delimiter(csv_content.encode('utf-8'))
        self.assertEqual(delimiter, ',')
    
    def test_handle_single_line(self):
        """Test handling of single line content"""
        csv_content = "ID,Name,Value"
        delimiter = detect_csv_delimiter(csv_content.encode('utf-8'))
        self.assertEqual(delimiter, ',')
    
    def test_handle_mixed_delimiters(self):
        """Test handling of content with mixed delimiters (should detect most common)"""
        csv_content = "ID,Name,Value;Extra\n1,Test,100;Data\n2,Test2,200;More"
        delimiter = detect_csv_delimiter(csv_content.encode('utf-8'))
        # Should detect comma as it appears more frequently
        self.assertEqual(delimiter, ',')
    
    def test_handle_large_content(self):
        """Test handling of large content (should only use sample)"""
        # Create a large CSV with semicolon delimiter
        lines = ["ID;Name;Value"] + [f"{i};Test{i};{i*100}" for i in range(1000)]
        csv_content = "\n".join(lines)
        delimiter = detect_csv_delimiter(csv_content.encode('utf-8'))
        self.assertEqual(delimiter, ';')
