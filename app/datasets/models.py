from django.db import models
from django.contrib.auth.models import User
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    target = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.timestamp}: {self.user} - {self.action} - {self.target}"


class DataSet(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_datasets')
    shared_with = models.ManyToManyField(User, related_name='shared_datasets', blank=True)
    shared_with_groups = models.ManyToManyField('auth.Group', related_name='shared_datasets', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=False)
    allow_multiple_entries = models.BooleanField(default=False, help_text="Allow multiple data entries per geometry point")

    def __str__(self):
        return self.name

    def can_access(self, user):
        """Check if a user can access this dataset"""
        if self.is_public:
            return True
        if user == self.owner:
            return True
        if user in self.shared_with.all():
            return True
        # Check if user is in any of the shared groups
        if self.shared_with_groups.filter(user=user).exists():
            return True
        return False

    class Meta:
        ordering = ['-created_at']


class DataGeometry(models.Model):
    dataset = models.ForeignKey(DataSet, on_delete=models.CASCADE, related_name='geometries')
    address = models.CharField(max_length=500)
    geometry = gis_models.PointField(srid=4326)  # WGS84 coordinate system
    id_kurz = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_geometries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id_kurz} - {self.address}"

    def save(self, *args, **kwargs):
        # Ensure the geometry is properly set if not already done
        if not self.geometry:
            # Default to a point if no geometry is provided
            self.geometry = Point(0, 0, srid=4326)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Data Geometries"
        unique_together = [['dataset', 'id_kurz']]


class DataEntry(models.Model):
    geometry = models.ForeignKey(DataGeometry, on_delete=models.CASCADE, related_name='entries')
    name = models.CharField(max_length=255, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_entries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        year_str = f" ({self.year})" if self.year else ""
        name_str = self.name or "Unnamed Entry"
        return f"{name_str} - {self.geometry.id_kurz}{year_str}"

    def get_field_value(self, field_name):
        """Get the value of a specific field for this entry"""
        try:
            field = self.fields.get(field_name=field_name)
            return field.value
        except DataEntryField.DoesNotExist:
            return None

    def set_field_value(self, field_name, value, field_type='text'):
        """Set the value of a specific field for this entry"""
        field, created = self.fields.get_or_create(
            field_name=field_name,
            defaults={'field_type': field_type, 'value': value}
        )
        if not created:
            field.value = value
            field.field_type = field_type
            field.save()
        return field

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Data Entries"


class DataEntryField(models.Model):
    """Dynamic field values for data entries - represents CSV columns"""
    FIELD_TYPE_CHOICES = [
        ('text', 'Text'),
        ('integer', 'Integer'),
        ('decimal', 'Decimal'),
        ('boolean', 'Boolean'),
        ('date', 'Date'),
        ('choice', 'Choice'),
    ]
    
    entry = models.ForeignKey(DataEntry, on_delete=models.CASCADE, related_name='fields')
    field_name = models.CharField(max_length=100, help_text="Field name (column name from CSV)")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, default='text')
    value = models.TextField(blank=True, null=True, help_text="Field value")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.entry.geometry.id_kurz} - {self.field_name}: {self.value}"

    def get_typed_value(self):
        """Get the value converted to the appropriate Python type"""
        if not self.value:
            return None
            
        try:
            if self.field_type == 'integer':
                return int(self.value)
            elif self.field_type == 'decimal':
                return float(self.value)
            elif self.field_type == 'boolean':
                return self.value.lower() in ('true', '1', 'yes', 'on')
            elif self.field_type == 'date':
                from datetime import datetime
                return datetime.strptime(self.value, '%Y-%m-%d').date()
            else:  # text, choice
                return str(self.value)
        except (ValueError, TypeError):
            return self.value

    class Meta:
        ordering = ['field_name']
        verbose_name = "Data Entry Field"
        verbose_name_plural = "Data Entry Fields"
        unique_together = ['entry', 'field_name']


class DataEntryFile(models.Model):
    entry = models.ForeignKey(DataEntry, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)  # e.g., 'image/jpeg', 'image/png'
    file_size = models.IntegerField()  # Size in bytes
    upload_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_files')
    upload_date = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.filename} - {self.entry.name}"

    def get_file_extension(self):
        """Get file extension from filename"""
        return self.filename.split('.')[-1].lower() if '.' in self.filename else ''

    def is_image(self):
        """Check if file is an image"""
        return self.file_type.startswith('image/')

    class Meta:
        ordering = ['-upload_date']
        verbose_name_plural = "Data Entry Files"


class Typology(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_typologies')
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Typologies"


class TypologyEntry(models.Model):
    typology = models.ForeignKey(Typology, on_delete=models.CASCADE, related_name='entries')
    code = models.IntegerField()
    category = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    
    def __str__(self):
        return f"{self.code} - {self.name} ({self.category})"
    
    class Meta:
        ordering = ['code']
        verbose_name_plural = "Typology Entries"
        unique_together = ['typology', 'code']


class DatasetFieldConfig(models.Model):
    """Configuration for dataset fields - allows customization of field names and visibility per dataset"""
    dataset = models.OneToOneField(DataSet, on_delete=models.CASCADE, related_name='field_config')
    
    # Usage Code fields
    usage_code1_label = models.CharField(max_length=100, default='Usage Code 1')
    usage_code1_enabled = models.BooleanField(default=True)
    usage_code2_label = models.CharField(max_length=100, default='Usage Code 2')
    usage_code2_enabled = models.BooleanField(default=True)
    usage_code3_label = models.CharField(max_length=100, default='Usage Code 3')
    usage_code3_enabled = models.BooleanField(default=True)
    
    # Category fields
    cat_inno_label = models.CharField(max_length=100, default='Category Innovation')
    cat_inno_enabled = models.BooleanField(default=True)
    cat_wert_label = models.CharField(max_length=100, default='Category Value')
    cat_wert_enabled = models.BooleanField(default=True)
    cat_fili_label = models.CharField(max_length=100, default='Category Filial')
    cat_fili_enabled = models.BooleanField(default=True)
    
    # Year field
    year_label = models.CharField(max_length=100, default='Year')
    year_enabled = models.BooleanField(default=True)
    
    # Entry name field
    name_label = models.CharField(max_length=100, default='Entry Name')
    name_enabled = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Field Config for {self.dataset.name}"
    
    class Meta:
        verbose_name = "Dataset Field Configuration"
        verbose_name_plural = "Dataset Field Configurations"


class DatasetField(models.Model):
    """Field configuration for datasets - defines which CSV columns are shown in data input"""
    FIELD_TYPE_CHOICES = [
        ('text', 'Text'),
        ('integer', 'Integer'),
        ('decimal', 'Decimal'),
        ('boolean', 'Boolean'),
        ('date', 'Date'),
        ('choice', 'Choice'),
    ]
    
    dataset = models.ForeignKey(DataSet, on_delete=models.CASCADE, related_name='dataset_fields')
    field_name = models.CharField(max_length=100, help_text="Field name (CSV column name)")
    label = models.CharField(max_length=100, help_text="Display label for the field")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, default='text')
    required = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    help_text = models.TextField(blank=True, null=True, help_text="Help text to display to users")
    choices = models.TextField(blank=True, null=True, help_text="Comma-separated choices for choice fields")
    order = models.PositiveIntegerField(default=0, help_text="Display order (0 = first)")
    is_coordinate_field = models.BooleanField(default=False, help_text="Whether this field represents coordinates")
    is_id_field = models.BooleanField(default=False, help_text="Whether this field is the unique identifier")
    is_address_field = models.BooleanField(default=False, help_text="Whether this field represents the address")
    typology = models.ForeignKey(Typology, on_delete=models.SET_NULL, null=True, blank=True, help_text="Typology to use for this field (for choice fields)")
    typology_category = models.CharField(max_length=100, blank=True, null=True, help_text="Limit typology options to a specific category")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.label} ({self.dataset.name})"
    
    def get_choices_list(self):
        """Get choices as a list for choice fields"""
        # If typology is assigned, use typology entries regardless of stored field_type
        if self.typology:
            entries = self.typology.entries.all()
            if self.typology_category:
                entries = entries.filter(category=self.typology_category)
            return [
                {'value': str(entry.code), 'label': f"{entry.code} - {entry.name}"}
                for entry in entries.order_by('code')
            ]
        # Otherwise, fall back to manual choices for choice fields
        if self.field_type == 'choice' and self.choices:
            return [choice.strip() for choice in self.choices.split(',') if choice.strip()]
        return []
    
    class Meta:
        ordering = ['order', 'field_name']
        verbose_name = "Dataset Field"
        verbose_name_plural = "Dataset Fields"
        unique_together = ['dataset', 'field_name']  # Field names must be unique per dataset


class ExportTask(models.Model):
    """Model to track file export tasks"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    dataset = models.ForeignKey(DataSet, on_delete=models.CASCADE, related_name='export_tasks')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='export_tasks')
    task_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file_path = models.CharField(max_length=500, blank=True, null=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Export parameters
    file_types = models.JSONField(default=list)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    organize_by = models.CharField(max_length=20, default='geometry')
    include_metadata = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Export Task {self.task_id} - {self.dataset.name}"
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Export Task"
        verbose_name_plural = "Export Tasks" 