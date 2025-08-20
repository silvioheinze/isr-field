# ISR Field

A Django application for managing spatial data with user authentication, data import/export capabilities, interactive mapping features, and typology management for standardized data categorization.

## Features

### Core Features
- **User Management**: Registration, authentication, and role-based access control
- **Dataset Management**: Create, edit, and manage datasets with access control (users and groups)
- **Spatial Data**: Store and manage geometry points with associated data
- **Data Import**: Import CSV files with automatic coordinate system detection
- **Data Export**: Export datasets as CSV with year-prefixed columns
- **Interactive Maps**: View and edit data on interactive maps with clustering and overlapping point handling
- **File Management**: Upload and manage files associated with data entries
- **Audit Logging**: Track user actions and data changes

### New Features

#### Typology Management
- **Typology Creation**: Create standardized categorization systems for data entries
- **Typology Entries**: Define codes, categories, and names for consistent data classification
- **CSV Import/Export**: Import typology entries from CSV files and export existing typologies
- **Dataset Integration**: Link typologies to datasets for standardized data entry
- **Usage Code Dropdowns**: Interactive dropdowns for selecting typology codes during data entry

#### Enhanced User Management
- **Staff/Admin Permissions**: Role-based access control using Django's `is_staff` and `is_superuser` fields
- **User Creation**: Administrators can create new users with specific permissions
- **User Editing**: Edit user details, permissions, and group memberships
- **Group Management**: Create and manage user groups with member assignment
- **Permission System**: Restricted dataset and typology creation to staff and admin users only

#### Improved Authentication
- **Custom Password Reset**: Complete password reset workflow with custom templates
- **Enhanced Login**: Redesigned login form with modern styling
- **User Registration**: Mobile-friendly registration form with validation
- **Profile Management**: User profile page with email and password change functionality

#### Enhanced Data Input Interface
- **Responsive Data Tables**: Transposed table layout with data entries as columns
- **AJAX Photo Upload**: Real-time file upload for data entry photos
- **Map Improvements**: Fixed zoom levels, circle markers, and overlapping point handling
- **Auto-generation**: Automatic ID generation for new geometry points
- **Copy Functionality**: Copy data from previous years to new entries

#### Design and UI Improvements
- **ISR Brand Colors**: Consistent color scheme using ISR brand colors (`#0047BB`, `#001A70`, `#92C1E9`)
- **Modern Templates**: Card-based layouts with Bootstrap 5 styling
- **Mobile Responsive**: Optimized for mobile devices with responsive design
- **Icon Integration**: Bootstrap Icons throughout the interface
- **Consistent Navigation**: Updated navigation with conditional display based on user permissions

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

## Production Deployment

The application includes a production-ready Docker setup with GitHub Actions for automated builds.

### Docker Images

- **Development**: `Dockerfile` - For local development
- **Production**: `Dockerfile.prod` - Multi-stage build with optimizations

### GitHub Container Registry

Images are automatically built and pushed to GitHub Container Registry on:
- Push to main/master branch
- Tagged releases (v*)
- Pull requests (for testing)

### Quick Deployment

1. **Set up environment variables**:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

2. **Test the production build**:
   ```bash
   ./test-production-build.sh
   ```

3. **Deploy using the script**:
   ```bash
   ./deploy.sh
   ```

4. **Manual deployment**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Environment Variables

Required environment variables for production:
- `DJANGO_SECRET_KEY`: Django secret key
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password

### Email Configuration (SMTP)

To enable password reset emails and other email functionality, configure SMTP settings:

```bash
# Email backend (use SMTP for production)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend

# SMTP server configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Email settings
DEFAULT_FROM_EMAIL=noreply@isrfield.dataplexity.eu
SERVER_EMAIL=server@isrfield.dataplexity.eu
EMAIL_SUBJECT_PREFIX=[ISR Field]
```

#### Common SMTP Providers

**Gmail**:
```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password  # Use App Password, not regular password
```

**Outlook/Hotmail**:
```bash
EMAIL_HOST=smtp-mail.outlook.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@outlook.com
EMAIL_HOST_PASSWORD=your-password
```

**Custom SMTP Server**:
```bash
EMAIL_HOST=your-smtp-server.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-username
EMAIL_HOST_PASSWORD=your-password
```

#### Testing Email Configuration

Test your SMTP configuration:
```bash
docker compose exec app python manage.py test_email --to your-email@example.com
```

### Health Checks

The application includes health check endpoints:
- **Health endpoint**: `http://localhost:8000/health/`
- **Docker health checks**: Automatic container health monitoring

## Typology Management

### Creating Typologies
Typologies provide standardized categorization for data entries across datasets:

1. **Access Typology Management**: Navigate to "Typologies" in the main menu
2. **Create New Typology**: Click "Create New Typology" button (staff/admin only)
3. **Define Entries**: Add typology entries with:
   - **Code**: Integer identifier for the entry
   - **Category**: Grouping category (e.g., "Residential", "Commercial")
   - **Name**: Descriptive name for the entry
4. **CSV Import**: Import typology entries from CSV files
5. **Assign to Datasets**: Link typologies to datasets for standardized data entry

### Typology CSV Format
Import typology entries using CSV files with the following format:
```csv
code,category,name
100,Residential,Residential Building
200,Commercial,Office Building
300,Industrial,Factory
```

### Usage in Data Entry
When a dataset has an assigned typology:
- **Usage Code Fields**: Display dropdown menus with typology entries
- **Auto-completion**: Select from predefined categories and codes
- **Consistency**: Ensures standardized data across datasets

## Data Import

### Enhanced CSV Import Features
- **Automatic Coordinate Detection**: Supports multiple coordinate systems:
  - WGS84 (LAT/LON, LATITUDE/LONGITUDE)
  - Austrian coordinate systems (EPSG:31256, 31257, 31258)
  - Scaled coordinates for various projections
- **Flexible Column Mapping**: Supports both year-prefixed and generic column names
- **Data Validation**: Handles missing data with social science coding (999 = missing)
- **Error Handling**: Comprehensive error reporting and validation

### CSV Import Format
The application supports various CSV formats:

**Standard Format**:
```csv
ID,ADRESSE,GEB_X,GEB_Y,2016_NUTZUNG,2016_CAT_INNO,2022_NUTZUNG,2022_CAT_INNO
test_001,Test Address 1,656610,3399131,870,999,870,999
test_002,Test Address 2,636410,3399724,640,0,640,0
```

**Alternative Coordinate Formats**:
```csv
ID,ADRESSE,X,Y,2016_NUTZUNG,2016_CAT_INNO
test_001,Test Address 1,16.3738,48.2082,870,999
```

**With Entry Names**:
```csv
ID,ADRESSE,GEB_X,GEB_Y,2016_NUTZUNG,2016_CAT_INNO,NUTZUNG_NAME
test_001,Test Address 1,656610,3399131,870,999,Residential Building
```

### Import Features
- **Coordinate System Detection**: Automatically detects coordinate system based on value ranges
- **Missing Data Handling**: Treats 'NA', 'N/A', 'NULL' as missing data
- **Social Science Coding**: Uses 999 for missing integer values
- **Entry Name Support**: Optional `NUTZUNG_NAME` column for entry descriptions

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

## Interactive Mapping

### Map Features
- **Fixed Zoom Level**: Maps maintain consistent zoom level (18) for detailed viewing
- **Circle Markers**: Data points displayed as circles instead of pins
- **Clustering**: Overlapping points are clustered for better visualization
- **Point Selection**: Interactive selection of overlapping points with detailed information
- **Full-width Display**: Maps use full available width for optimal viewing

### Data Entry Interface
- **Responsive Tables**: Data entries displayed in transposed table format
- **Year-based Columns**: Each year's data displayed in separate columns
- **Copy Functionality**: Copy data from previous years to new entries
- **Photo Upload**: AJAX-based photo upload for data entries
- **Auto-generation**: Automatic ID generation for new geometry points

## Access Control

The application supports flexible access control for datasets:

### Access Levels

1. **Owner**: The user who created the dataset (always has full access)
2. **Individual Users**: Specific users granted direct access
3. **Groups**: All members of selected user groups have access
4. **Public**: Anyone can access the dataset (if enabled)

### Permission System

#### User Roles
- **Regular Users**: Can view and interact with accessible datasets
- **Staff Users**: Can create datasets, typologies, and manage users
- **Superusers**: Full administrative access to all features

#### Restricted Features
- **Dataset Creation**: Only staff and superusers can create new datasets
- **Typology Creation**: Only staff and superusers can create typologies
- **User Management**: Only staff and superusers can manage users and groups

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

## User Interface

### Design System
- **ISR Brand Colors**: Primary (`#0047BB`), Secondary (`#001A70`), Accent (`#92C1E9`)
- **Bootstrap 5**: Modern responsive framework
- **Bootstrap Icons**: Consistent iconography throughout
- **Card-based Layout**: Clean, organized interface design

### Responsive Design
- **Mobile Optimized**: Touch-friendly interface for mobile devices
- **Tablet Support**: Optimized layouts for tablet screens
- **Desktop Experience**: Full-featured interface for desktop users

### Navigation
- **Conditional Display**: Navigation items shown based on user permissions
- **Breadcrumb Navigation**: Clear navigation paths
- **Quick Actions**: Contextual action buttons throughout the interface

## Security Features

### Authentication
- **Custom Password Reset**: Secure password reset workflow
- **Session Management**: Proper session handling and security
- **CSRF Protection**: Cross-site request forgery protection
- **Permission Checks**: Server-side validation of all user actions

### Data Protection
- **Access Control**: Granular access control for all data
- **Audit Logging**: Comprehensive logging of user actions
- **Input Validation**: Server-side validation of all user inputs
- **File Upload Security**: Secure file upload handling

## Technical Architecture

### Backend
- **Django 5.2**: Modern Python web framework
- **PostgreSQL**: Robust relational database with PostGIS extension
- **Django ORM**: Object-relational mapping for database operations
- **Django Admin**: Built-in administrative interface

### Frontend
- **Bootstrap 5**: Responsive CSS framework
- **Leaflet.js**: Interactive mapping library
- **AJAX**: Asynchronous data loading and form submission
- **JavaScript**: Modern ES6+ JavaScript for enhanced interactivity

### Deployment
- **Docker**: Containerized deployment
- **Nginx**: High-performance web server
- **PostgreSQL**: Production-ready database
- **GitHub Actions**: Automated CI/CD pipeline


