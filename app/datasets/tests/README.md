# Test Structure

This directory contains the test files for the datasets app, organized into logical modules for better maintainability.

## Test Files

### `test_models.py`
- **DatasetFieldConfigModelTest**: Tests for the DatasetFieldConfig model
- **DatasetFieldModelTest**: Tests for the DatasetField model

### `test_dataset_field_config_form.py`
- **DatasetFieldConfigFormTest**: Tests for the DatasetFieldConfigForm

### `test_dataset_field_form.py`
- **DatasetFieldFormTest**: Tests for the DatasetFieldForm

### `test_group_form.py`
- **GroupFormTest**: Tests for the GroupForm

### `test_views.py`
- **DatasetFieldConfigViewTest**: Tests for field configuration views
- **DatasetFieldViewTest**: Tests for custom field management views

### `test_integration.py`
- **DatasetFieldConfigIntegrationTest**: Integration tests for field configuration workflow
- **DatasetFieldIntegrationTest**: Integration tests for custom field management workflow

### `test_csv_delimiter.py`
- **CSVDelimiterDetectionTest**: Tests for CSV delimiter auto-detection functionality

### `test_formsets.py`
- **DatasetFieldInlineFormSetTest**: Tests for formset functionality

### `test_django_forms.py`
- **DjangoBuiltInFormsTest**: Tests for Django built-in forms (UserCreation, PasswordChange, etc.)

### `test_form_integration.py`
- **FormIntegrationTest**: Integration tests for forms working together

## Running Tests

To run all tests:
```bash
docker-compose exec app python manage.py test datasets.tests
```

To run specific test files:
```bash
docker-compose exec app python manage.py test datasets.tests.test_models
docker-compose exec app python manage.py test datasets.tests.test_dataset_field_config_form
docker-compose exec app python manage.py test datasets.tests.test_dataset_field_form
docker-compose exec app python manage.py test datasets.tests.test_group_form
```

To run specific test classes:
```bash
docker-compose exec app python manage.py test datasets.tests.test_models.DatasetFieldConfigModelTest
```

## Test Organization Benefits

1. **Modularity**: Each test file focuses on a specific aspect of the application
2. **Maintainability**: Easier to find and update specific tests
3. **Readability**: Smaller files are easier to navigate and understand
4. **Parallel Execution**: Django can run different test modules in parallel
5. **Focused Testing**: Developers can run only the tests relevant to their changes

## Test Coverage

The test suite covers:
- Model creation, validation, and relationships
- Form validation and data handling
- View permissions and functionality
- Integration workflows
- CSV processing features
- Django built-in form functionality
- Formset operations
