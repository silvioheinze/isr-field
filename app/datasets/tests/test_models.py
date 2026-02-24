from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.contrib.gis.geos import Point
from ..models import DataSet, DatasetFieldConfig, DataGeometry, DataEntry, DataEntryField, Typology, TypologyEntry, DatasetField


class DatasetFieldConfigModelTest(TestCase):
    """Test cases for DatasetFieldConfig model"""
    
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
    
    def test_dataset_field_config_creation(self):
        """Test creating a DatasetFieldConfig"""
        config = DatasetFieldConfig.objects.create(dataset=self.dataset)
        
        self.assertEqual(config.dataset, self.dataset)
        self.assertEqual(config.usage_code1_label, 'Usage Code 1')
        self.assertEqual(config.usage_code2_label, 'Usage Code 2')
        self.assertEqual(config.usage_code3_label, 'Usage Code 3')
        self.assertEqual(config.cat_inno_label, 'Category Innovation')
        self.assertEqual(config.cat_wert_label, 'Category Value')
        self.assertEqual(config.cat_fili_label, 'Category Filial')
        self.assertEqual(config.year_label, 'Year')
        self.assertEqual(config.name_label, 'Entry Name')
        
        # Test default enabled states
        self.assertTrue(config.usage_code1_enabled)
        self.assertTrue(config.usage_code2_enabled)
        self.assertTrue(config.usage_code3_enabled)
        self.assertTrue(config.cat_inno_enabled)
        self.assertTrue(config.cat_wert_enabled)
        self.assertTrue(config.cat_fili_enabled)
        self.assertTrue(config.year_enabled)
        self.assertTrue(config.name_enabled)
    
    def test_dataset_field_config_str(self):
        """Test string representation of DatasetFieldConfig"""
        config = DatasetFieldConfig.objects.create(dataset=self.dataset)
        expected_str = f"Field Config for {self.dataset.name}"
        self.assertEqual(str(config), expected_str)
    
    def test_dataset_field_config_custom_values(self):
        """Test setting custom values for field config"""
        config = DatasetFieldConfig.objects.create(
            dataset=self.dataset,
            usage_code1_label='Custom Usage 1',
            usage_code1_enabled=False,
            cat_inno_label='Custom Innovation',
            cat_inno_enabled=False,
            year_label='Custom Year',
            year_enabled=True
        )
        
        self.assertEqual(config.usage_code1_label, 'Custom Usage 1')
        self.assertFalse(config.usage_code1_enabled)
        self.assertEqual(config.cat_inno_label, 'Custom Innovation')
        self.assertFalse(config.cat_inno_enabled)
        self.assertEqual(config.year_label, 'Custom Year')
        self.assertTrue(config.year_enabled)
    
    def test_dataset_field_config_one_to_one_relationship(self):
        """Test that each dataset can only have one field config"""
        # Create first config
        config1 = DatasetFieldConfig.objects.create(dataset=self.dataset)
        
        # Try to create another config for the same dataset
        with self.assertRaises(IntegrityError):
            DatasetFieldConfig.objects.create(dataset=self.dataset)
    
    def test_dataset_field_config_cascade_delete(self):
        """Test that field config is deleted when dataset is deleted"""
        config = DatasetFieldConfig.objects.create(dataset=self.dataset)
        config_id = config.id
        
        # Delete the dataset
        self.dataset.delete()
        
        # Check that the config is also deleted
        self.assertFalse(DatasetFieldConfig.objects.filter(id=config_id).exists())


class DatasetFieldModelTest(TestCase):
    """Test cases for DatasetField model"""
    
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
    
    def test_custom_field_creation(self):
        """Test creating a DatasetField"""
        field = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='test_field',
            label='Test Field',
            field_type='text',
            required=True,
            enabled=True,
            help_text='This is a test field',
            order=1
        )
        
        self.assertEqual(field.dataset, self.dataset)
        self.assertEqual(field.field_name, 'test_field')
        self.assertEqual(field.label, 'Test Field')
        self.assertEqual(field.field_type, 'text')
        self.assertTrue(field.required)
        self.assertTrue(field.enabled)
        self.assertEqual(field.help_text, 'This is a test field')
        self.assertEqual(field.order, 1)
    
    def test_custom_field_str(self):
        """Test string representation of DatasetField"""
        field = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='test_field',
            label='Test Field',
            field_type='text'
        )
        expected_str = f"Test Field ({self.dataset.name})"
        self.assertEqual(str(field), expected_str)
    
    def test_custom_field_unique_constraint(self):
        """Test unique constraint on dataset and field_name"""
        DatasetField.objects.create(
            dataset=self.dataset,
            field_name='test_field',
            label='Test Field',
            field_type='text'
        )
        
        # Try to create another field with same name for same dataset
        with self.assertRaises(IntegrityError):
            DatasetField.objects.create(
                dataset=self.dataset,
                field_name='test_field',
                label='Another Test Field',
                field_type='integer'
            )
    
    def test_custom_field_cascade_delete(self):
        """Test that custom fields are deleted when dataset is deleted"""
        field = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='test_field',
            label='Test Field',
            field_type='text'
        )
        field_id = field.id
        
        # Delete the dataset
        self.dataset.delete()
        
        # Check that the field is also deleted
        self.assertFalse(DatasetField.objects.filter(id=field_id).exists())
    
    def test_custom_field_choices_list(self):
        """Test get_choices_list method"""
        field = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='choice_field',
            label='Choice Field',
            field_type='choice',
            choices='Option 1, Option 2, Option 3'
        )
        
        choices = field.get_choices_list()
        expected_choices = ['Option 1', 'Option 2', 'Option 3']
        self.assertEqual(choices, expected_choices)
    
    def test_custom_field_choices_list_empty(self):
        """Test get_choices_list method with empty choices"""
        field = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='choice_field',
            label='Choice Field',
            field_type='choice',
            choices=''
        )
        
        choices = field.get_choices_list()
        self.assertEqual(choices, [])

    def test_typology_choices_list_for_non_choice_field(self):
        """Typology fields should return typology entries even if stored as text"""
        typology = Typology.objects.create(name='Test Typology', created_by=self.user)
        TypologyEntry.objects.create(typology=typology, code=1, category='A', name='Option 1')
        TypologyEntry.objects.create(typology=typology, code=2, category='B', name='Option 2')

        field = DatasetField.objects.create(
            dataset=self.dataset,
            field_name='typology_field',
            label='Typology Field',
            field_type='text',
            typology=typology
        )

        choices = field.get_choices_list()
        self.assertEqual(len(choices), 2)
        self.assertEqual(choices[0]['value'], '1')
        self.assertIn('Option 1', choices[0]['label'])


class DataEntryFieldModelTest(TestCase):
    """Test cases for DataEntryField model"""
    
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
            owner=self.user,
            is_public=False
        )
        self.geometry = DataGeometry.objects.create(
            dataset=self.dataset,
            id_kurz='TEST001',
            address='Test Address 123',
            geometry=Point(16.3738, 48.2082),  # Vienna coordinates
            user=self.user
        )
        self.entry = DataEntry.objects.create(
            geometry=self.geometry,
            name='Test Entry',
            year=2024,
            user=self.user
        )
    
    def test_data_entry_field_creation(self):
        """Test creating a DataEntryField"""
        field = DataEntryField.objects.create(
            entry=self.entry,
            field_name='test_field',
            field_type='text',
            value='Test Value'
        )
        
        self.assertEqual(field.entry, self.entry)
        self.assertEqual(field.field_name, 'test_field')
        self.assertEqual(field.field_type, 'text')
        self.assertEqual(field.value, 'Test Value')
        self.assertIsNotNone(field.created_at)
        self.assertIsNotNone(field.updated_at)
    
    def test_data_entry_field_str_representation(self):
        """Test string representation of DataEntryField"""
        field = DataEntryField.objects.create(
            entry=self.entry,
            field_name='test_field',
            field_type='text',
            value='Test Value'
        )
        
        expected_str = f"{self.entry.geometry.id_kurz} - {field.field_name}: {field.value}"
        self.assertEqual(str(field), expected_str)
    
    def test_data_entry_field_unique_together(self):
        """Test that entry and field_name combination is unique"""
        DataEntryField.objects.create(
            entry=self.entry,
            field_name='test_field',
            field_type='text',
            value='Test Value'
        )
        
        # Try to create another field with same entry and field_name
        with self.assertRaises(IntegrityError):
            DataEntryField.objects.create(
                entry=self.entry,
                field_name='test_field',
                field_type='integer',
                value='123'
            )
    
    def test_get_typed_value_text(self):
        """Test get_typed_value for text field type"""
        field = DataEntryField.objects.create(
            entry=self.entry,
            field_name='text_field',
            field_type='text',
            value='Hello World'
        )
        
        self.assertEqual(field.get_typed_value(), 'Hello World')

    def test_get_typed_value_textarea(self):
        """Test get_typed_value for textarea (Large Text) field type"""
        field = DataEntryField.objects.create(
            entry=self.entry,
            field_name='notes_field',
            field_type='textarea',
            value='Line one\nLine two\nLine three'
        )
        
        self.assertEqual(field.get_typed_value(), 'Line one\nLine two\nLine three')
        self.assertIsInstance(field.get_typed_value(), str)
    
    def test_get_typed_value_integer(self):
        """Test get_typed_value for integer field type"""
        field = DataEntryField.objects.create(
            entry=self.entry,
            field_name='int_field',
            field_type='integer',
            value='42'
        )
        
        self.assertEqual(field.get_typed_value(), 42)
        self.assertIsInstance(field.get_typed_value(), int)
    
    def test_get_typed_value_integer_invalid(self):
        """Test get_typed_value for integer field type with invalid value"""
        field = DataEntryField.objects.create(
            entry=self.entry,
            field_name='int_field',
            field_type='integer',
            value='not_a_number'
        )
        
        # Should return the original value when conversion fails
        self.assertEqual(field.get_typed_value(), 'not_a_number')
    
    def test_get_typed_value_decimal(self):
        """Test get_typed_value for decimal field type"""
        field = DataEntryField.objects.create(
            entry=self.entry,
            field_name='decimal_field',
            field_type='decimal',
            value='3.14159'
        )
        
        self.assertEqual(field.get_typed_value(), 3.14159)
        self.assertIsInstance(field.get_typed_value(), float)
    
    def test_get_typed_value_decimal_invalid(self):
        """Test get_typed_value for decimal field type with invalid value"""
        field = DataEntryField.objects.create(
            entry=self.entry,
            field_name='decimal_field',
            field_type='decimal',
            value='not_a_number'
        )
        
        # Should return the original value when conversion fails
        self.assertEqual(field.get_typed_value(), 'not_a_number')
    
    def test_get_typed_value_boolean_true(self):
        """Test get_typed_value for boolean field type with true values"""
        true_values = ['true', 'TRUE', 'True', '1', 'yes', 'YES', 'on', 'ON']
        
        for value in true_values:
            field = DataEntryField.objects.create(
                entry=self.entry,
                field_name=f'bool_field_{value}',
                field_type='boolean',
                value=value
            )
            self.assertTrue(field.get_typed_value(), f"Value '{value}' should be True")
    
    def test_get_typed_value_boolean_false(self):
        """Test get_typed_value for boolean field type with false values"""
        false_values = ['false', 'FALSE', 'False', '0', 'no', 'NO', 'off', 'OFF', 'anything_else']
        
        for value in false_values:
            field = DataEntryField.objects.create(
                entry=self.entry,
                field_name=f'bool_field_{value}',
                field_type='boolean',
                value=value
            )
            self.assertFalse(field.get_typed_value(), f"Value '{value}' should be False")
    
    def test_get_typed_value_date(self):
        """Test get_typed_value for date field type"""
        field = DataEntryField.objects.create(
            entry=self.entry,
            field_name='date_field',
            field_type='date',
            value='2024-01-15'
        )
        
        from datetime import date
        expected_date = date(2024, 1, 15)
        self.assertEqual(field.get_typed_value(), expected_date)
        self.assertIsInstance(field.get_typed_value(), date)
    
    def test_get_typed_value_date_invalid(self):
        """Test get_typed_value for date field type with invalid value"""
        field = DataEntryField.objects.create(
            entry=self.entry,
            field_name='date_field',
            field_type='date',
            value='invalid_date'
        )
        
        # Should return the original value when conversion fails
        self.assertEqual(field.get_typed_value(), 'invalid_date')
    
    def test_get_typed_value_choice(self):
        """Test get_typed_value for choice field type"""
        field = DataEntryField.objects.create(
            entry=self.entry,
            field_name='choice_field',
            field_type='choice',
            value='Option A'
        )
        
        self.assertEqual(field.get_typed_value(), 'Option A')
        self.assertIsInstance(field.get_typed_value(), str)
    
    def test_get_typed_value_none(self):
        """Test get_typed_value with None value"""
        field = DataEntryField.objects.create(
            entry=self.entry,
            field_name='empty_field',
            field_type='text',
            value=None
        )
        
        self.assertIsNone(field.get_typed_value())
    
    def test_get_typed_value_empty_string(self):
        """Test get_typed_value with empty string"""
        field = DataEntryField.objects.create(
            entry=self.entry,
            field_name='empty_field',
            field_type='text',
            value=''
        )
        
        self.assertIsNone(field.get_typed_value())
    
    def test_field_type_choices(self):
        """Test that field_type choices are valid"""
        valid_choices = ['text', 'textarea', 'integer', 'decimal', 'boolean', 'date', 'choice']
        
        for choice in valid_choices:
            field = DataEntryField.objects.create(
                entry=self.entry,
                field_name=f'field_{choice}',
                field_type=choice,
                value='test'
            )
            self.assertEqual(field.field_type, choice)
    
    def test_ordering(self):
        """Test that DataEntryField objects are ordered by field_name"""
        # Create fields in random order
        DataEntryField.objects.create(
            entry=self.entry,
            field_name='z_field',
            field_type='text',
            value='Z'
        )
        DataEntryField.objects.create(
            entry=self.entry,
            field_name='a_field',
            field_type='text',
            value='A'
        )
        DataEntryField.objects.create(
            entry=self.entry,
            field_name='m_field',
            field_type='text',
            value='M'
        )
        
        fields = DataEntryField.objects.filter(entry=self.entry)
        field_names = [field.field_name for field in fields]
        
        self.assertEqual(field_names, ['a_field', 'm_field', 'z_field'])
    
    def test_verbose_names(self):
        """Test verbose names in Meta class"""
        self.assertEqual(DataEntryField._meta.verbose_name, "Data Entry Field")
        self.assertEqual(DataEntryField._meta.verbose_name_plural, "Data Entry Fields")
    
    def test_related_name(self):
        """Test that related_name 'fields' works correctly"""
        DataEntryField.objects.create(
            entry=self.entry,
            field_name='test_field1',
            field_type='text',
            value='Value 1'
        )
        DataEntryField.objects.create(
            entry=self.entry,
            field_name='test_field2',
            field_type='text',
            value='Value 2'
        )
        
        # Test accessing fields through the entry
        fields = self.entry.fields.all()
        self.assertEqual(fields.count(), 2)
        
        field_names = [field.field_name for field in fields]
        self.assertIn('test_field1', field_names)
        self.assertIn('test_field2', field_names)
    
    def test_cascade_delete(self):
        """Test that DataEntryField is deleted when DataEntry is deleted"""
        field = DataEntryField.objects.create(
            entry=self.entry,
            field_name='test_field',
            field_type='text',
            value='Test Value'
        )
        
        field_id = field.id
        self.entry.delete()
        
        # Field should be deleted due to CASCADE
        self.assertFalse(DataEntryField.objects.filter(id=field_id).exists())
    
    def test_help_text(self):
        """Test help text for fields"""
        field = DataEntryField.objects.create(
            entry=self.entry,
            field_name='test_field',
            field_type='text',
            value='Test Value'
        )
        
        # Check that help text is set correctly
        self.assertEqual(field._meta.get_field('field_name').help_text, "Field name (column name from CSV)")
        self.assertEqual(field._meta.get_field('value').help_text, "Field value")
    
    def test_max_length_constraints(self):
        """Test max length constraints"""
        # Test field_name max length (100)
        long_field_name = 'x' * 101
        with self.assertRaises(Exception):  # Should raise ValidationError or similar
            field = DataEntryField(
                entry=self.entry,
                field_name=long_field_name,
                field_type='text',
                value='test'
            )
            field.full_clean()
        
        # Test field_type max length (20)
        long_field_type = 'x' * 21
        with self.assertRaises(Exception):  # Should raise ValidationError or similar
            field = DataEntryField(
                entry=self.entry,
                field_name='test_field',
                field_type=long_field_type,
                value='test'
            )
            field.full_clean()
