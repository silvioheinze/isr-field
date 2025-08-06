# isr-field

A Django application for managing spatial data with user authentication, data import/export capabilities, and interactive mapping features.

## Features

- **User Management**: Registration, authentication, and role-based access control
- **Dataset Management**: Create, edit, and manage datasets with access control (users and groups)
- **Spatial Data**: Store and manage geometry points with associated data
- **Data Import**: Import CSV files with automatic coordinate system detection
- **Data Export**: Export datasets as CSV with year-prefixed columns
- **Interactive Maps**: View and edit data on interactive maps
- **File Management**: Upload and manage files associated with data entries
- **Audit Logging**: Track user actions and data changes

## Development

```bash
# Create database migrations
docker compose exec app python manage.py makemigrations

# Start the application
docker compose up -d

# Apply migrations
docker compose exec app python manage.py migrate

# Create superuser
docker compose exec app python manage.py createsuperuser
```

## Data Export

The application supports exporting datasets as CSV files with the following features:

- **Geometry-based rows**: Each geometry point becomes a row in the CSV
- **Year-prefixed columns**: Data entries are organized by year (e.g., `2016_USAGE_CODE1`, `2022_CAT_INNO`)
- **Configurable options**: Choose whether to include coordinates and empty years
- **Automatic formatting**: Proper CSV formatting with headers and data validation

### Export Format

The exported CSV contains:
- `ID`: Unique identifier for each geometry
- `ADRESSE`: Address of the geometry
- `GEB_X`, `GEB_Y`: Coordinates (optional)
- Year-prefixed columns for each data field:
  - `USAGE_CODE1`, `USAGE_CODE2`, `USAGE_CODE3`
  - `CAT_INNO`, `CAT_WERT`, `CAT_FILI`

### Example Export

```csv
ID,ADRESSE,GEB_X,GEB_Y,2016_USAGE_CODE1,2016_CAT_INNO,2022_USAGE_CODE1,2022_CAT_INNO
test_001,Test Address 1,16.3738,48.2082,100,1,100,1
test_002,Test Address 2,16.3748,48.2092,101,2,101,2
```

## Access Control

The application supports flexible access control for datasets:

### Access Levels

1. **Owner**: The user who created the dataset (always has full access)
2. **Individual Users**: Specific users granted direct access
3. **Groups**: All members of selected user groups have access
4. **Public**: Anyone can access the dataset (if enabled)

### Access Management

- Dataset owners can manage access through the "Manage Access" interface
- Users can be added/removed individually or through group membership
- Access changes are logged for audit purposes
- Group membership automatically grants access to all datasets shared with that group

### Access Priority

1. **Public datasets**: Accessible to everyone
2. **Owner access**: Dataset creator always has access
3. **Individual user access**: Directly shared users have access
4. **Group access**: Users in shared groups have access


