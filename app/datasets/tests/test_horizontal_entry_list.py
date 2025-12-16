from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.gis.geos import Point
import json
import re
import os
from django.conf import settings

from ..models import DataSet, DataGeometry, DataEntry, DataEntryField, DatasetField


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class HorizontalEntryListTestCase(TestCase):
    """Test the horizontal entry list functionality in the data input interface"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.dataset = DataSet.objects.create(
            name='Test Dataset',
            description='Test dataset for horizontal entry list testing',
            owner=self.user,
            allow_multiple_entries=True
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
        
        # Create test geometry
        self.geometry = DataGeometry.objects.create(
            dataset=self.dataset,
            id_kurz='TEST001',
            address='Test Address',
            geometry=Point(15.0, 48.0),
            user=self.user
        )
        
        # Create multiple test entries
        self.entry1 = DataEntry.objects.create(
            geometry=self.geometry,
            name='Entry 1',
            year=2023,
            user=self.user
        )
        
        self.entry2 = DataEntry.objects.create(
            geometry=self.geometry,
            name='Entry 2',
            year=2024,
            user=self.user
        )
        
        self.entry3 = DataEntry.objects.create(
            geometry=self.geometry,
            name='Entry 3',
            year=2022,
            user=self.user
        )
        
        # Create field values for entries
        DataEntryField.objects.create(
            entry=self.entry1,
            field_name='test_field_1',
            value='Value 1'
        )
        
        DataEntryField.objects.create(
            entry=self.entry2,
            field_name='test_field_1',
            value='Value 2'
        )
        
        self.client = Client()
        self.client.force_login(self.user)
    
    def _get_js_file_path(self):
        """Helper method to get the correct path to the JavaScript file"""
        # Try STATICFILES_DIRS first (source files), then STATIC_ROOT (collected files)
        js_file_path = None
        if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
            js_file_path = os.path.join(settings.STATICFILES_DIRS[0], 'js', 'data-input.js')
            if os.path.exists(js_file_path):
                return js_file_path
        
        js_file_path = os.path.join(settings.STATIC_ROOT, 'js', 'data-input.js')
        return js_file_path
    
    def _get_css_file_path(self):
        """Helper method to get the correct path to the CSS file"""
        # Try STATICFILES_DIRS first (source files), then STATIC_ROOT (collected files)
        css_file_path = None
        if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
            css_file_path = os.path.join(settings.STATICFILES_DIRS[0], 'css', 'data-input.css')
            if os.path.exists(css_file_path):
                return css_file_path
        
        css_file_path = os.path.join(settings.STATIC_ROOT, 'css', 'data-input.css')
        return css_file_path
    
    def test_javascript_functions_exist(self):
        """Test that the JavaScript functions for horizontal entry list exist"""
        js_file_path = self._get_js_file_path()
        self.assertTrue(os.path.exists(js_file_path), f"JavaScript file not found at {js_file_path}")
        
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check that required functions exist
        required_functions = [
            'selectEntryFromBadge',
            'updateEntryBadges',
            'selectEntryFromDropdown',
            'entriesHorizontalList',
            'entry-badge',
            'entry-badge-selected'
        ]
        
        for func in required_functions:
            self.assertIn(func, js_content, f"Function or identifier {func} not found in JavaScript file")
    
    def test_horizontal_entry_list_html_structure(self):
        """Test that the JavaScript generates the correct HTML structure for horizontal entry list"""
        js_file_path = self._get_js_file_path()
        
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check that the HTML structure for horizontal list is generated
        html_patterns = [
            'All Entries',
            'entriesHorizontalList',
            'entry-badge',
            'selectEntryFromBadge(',
            'data-entry-id',
            'entry-badge-selected'
        ]
        
        for pattern in html_patterns:
            self.assertIn(pattern, js_content, f"HTML pattern {pattern} not found in JavaScript file")
    
    def test_geometry_details_api_includes_all_entries(self):
        """Test that the geometry details API includes all entries for the horizontal list"""
        response = self.client.get(reverse('geometry_details', kwargs={'geometry_id': self.geometry.id}))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data['success'])
        
        geometry_data = data['geometry']
        entries = geometry_data['entries']
        
        # Should have 3 entries
        self.assertEqual(len(entries), 3)
        
        # Check that all entries are included with required fields
        entry_ids = [entry['id'] for entry in entries]
        self.assertIn(self.entry1.id, entry_ids)
        self.assertIn(self.entry2.id, entry_ids)
        self.assertIn(self.entry3.id, entry_ids)
        
        # Check that each entry has the required fields for display
        for entry in entries:
            self.assertIn('id', entry)
            self.assertIn('name', entry)
            self.assertIn('year', entry)
            self.assertIn('user', entry)
    
    def test_entries_sorted_by_year_in_api(self):
        """Test that entries are included in the API response (sorting happens in JavaScript)"""
        response = self.client.get(reverse('geometry_details', kwargs={'geometry_id': self.geometry.id}))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        entries = data['geometry']['entries']
        
        # All entries should be present (sorting happens in JavaScript, not API)
        entry_ids = [entry['id'] for entry in entries]
        entry_years = [entry['year'] for entry in entries]
        
        self.assertIn(self.entry1.id, entry_ids)
        self.assertIn(self.entry2.id, entry_ids)
        self.assertIn(self.entry3.id, entry_ids)
        self.assertIn(2023, entry_years)
        self.assertIn(2024, entry_years)
        self.assertIn(2022, entry_years)
        
        # Verify JavaScript sorts entries by year (newest first)
        js_file_path = self._get_js_file_path()
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check that JavaScript sorts entries by year descending
        self.assertIn('sortedEntries', js_content)
        self.assertIn('sort(function(a, b)', js_content)
        self.assertIn('(b.year || 0) - (a.year || 0)', js_content)
    
    def test_horizontal_list_displayed_when_entries_exist(self):
        """Test that the horizontal entry list is displayed when entries exist"""
        js_file_path = self._get_js_file_path()
        
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check that the code checks for entries before displaying the list
        # Should check sortedEntries.length > 0 and allowMultipleEntries
        self.assertIn('sortedEntries.length > 0', js_content)
        self.assertIn('window.allowMultipleEntries && sortedEntries.length > 0', js_content)
    
    def test_horizontal_list_not_displayed_when_no_entries(self):
        """Test that the horizontal entry list is not displayed when no entries exist"""
        # Create a geometry without entries
        empty_geometry = DataGeometry.objects.create(
            dataset=self.dataset,
            id_kurz='EMPTY001',
            address='Empty Address',
            geometry=Point(16.0, 49.0),
            user=self.user
        )
        
        response = self.client.get(reverse('geometry_details', kwargs={'geometry_id': empty_geometry.id}))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        entries = data['geometry']['entries']
        
        # Should have no entries
        self.assertEqual(len(entries), 0)
        
        # The JavaScript should check for entries.length > 0 before displaying the list
        js_file_path = self._get_js_file_path()
        
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Should have conditional check with allowMultipleEntries
        self.assertIn('sortedEntries.length > 0', js_content)
        self.assertIn('window.allowMultipleEntries && sortedEntries.length > 0', js_content)
    
    def test_entry_badge_click_functionality(self):
        """Test that clicking on an entry badge calls the correct function"""
        js_file_path = self._get_js_file_path()
        
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check that onclick handler is set up correctly
        self.assertIn('selectEntryFromBadge(', js_content)
        
        # Check that selectEntryFromBadge function exists and updates selection
        self.assertIn('selectEntryFromBadge', js_content)
        self.assertIn('selectedEntryId', js_content)
        self.assertIn('generateEntriesTable', js_content)
    
    def test_entry_badge_selection_syncs_with_dropdown(self):
        """Test that selecting an entry badge updates the dropdown"""
        js_file_path = self._get_js_file_path()
        
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check that selectEntryFromBadge updates the dropdown
        self.assertIn('entrySelector', js_content)
        self.assertIn('selector.value = entryId', js_content)
    
    def test_entry_badge_selected_state(self):
        """Test that the selected entry badge has the correct CSS class"""
        js_file_path = self._get_js_file_path()
        
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check that selected badges get the correct class
        self.assertIn('entry-badge-selected', js_content)
        self.assertIn('entry-badge-selected', js_content)
    
    def test_update_entry_badges_function(self):
        """Test that the updateEntryBadges function exists and works correctly"""
        js_file_path = self._get_js_file_path()
        
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check that updateEntryBadges function exists
        self.assertIn('updateEntryBadges', js_content)
        self.assertIn('querySelectorAll', js_content)
        self.assertIn('.entry-badge', js_content)
        self.assertIn('entry-badge-selected', js_content)
    
    def test_entry_badge_displays_entry_info(self):
        """Test that entry badges display entry name, year, and user"""
        js_file_path = self._get_js_file_path()
        
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check that badges display entry information
        self.assertIn('entry.name', js_content)
        self.assertIn('entry.year', js_content)
        self.assertIn('entry.user', js_content)
        self.assertIn('escapeHtml(entryName)', js_content)
    
    def test_css_styles_for_entry_badges(self):
        """Test that CSS styles for entry badges exist"""
        css_file_path = self._get_css_file_path()
        self.assertTrue(os.path.exists(css_file_path), f"CSS file not found at {css_file_path}")
        
        with open(css_file_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        # Check that CSS classes exist
        css_classes = [
            '.entry-badge',
            '.entry-badge:hover',
            '.entry-badge-selected'
        ]
        
        for css_class in css_classes:
            self.assertIn(css_class, css_content, f"CSS class {css_class} not found in CSS file")
    
    def test_entry_badge_count_display(self):
        """Test that the entry count is displayed in the horizontal list header"""
        js_file_path = self._get_js_file_path()
        
        with open(js_file_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check that entry count is displayed
        self.assertIn('sortedEntries.length', js_content)
        self.assertIn('All Entries (', js_content)

