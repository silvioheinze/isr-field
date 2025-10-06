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
    typology = models.ForeignKey('Typology', on_delete=models.SET_NULL, null=True, blank=True, related_name='datasets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=False)

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
    id_kurz = models.CharField(max_length=100, unique=True)
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


class DataEntry(models.Model):
    geometry = models.ForeignKey(DataGeometry, on_delete=models.CASCADE, related_name='entries')
    name = models.CharField(max_length=255)
    usage_code1 = models.IntegerField()
    usage_code2 = models.IntegerField()
    usage_code3 = models.IntegerField()
    cat_inno = models.IntegerField()
    cat_wert = models.IntegerField()
    cat_fili = models.IntegerField()
    year = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_entries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.geometry.id_kurz} ({self.year})"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Data Entries"


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


class CustomField(models.Model):
    """Custom fields that can be added to datasets"""
    FIELD_TYPE_CHOICES = [
        ('text', 'Text'),
        ('integer', 'Integer'),
        ('decimal', 'Decimal'),
        ('boolean', 'Boolean'),
        ('date', 'Date'),
        ('choice', 'Choice'),
    ]
    
    dataset = models.ForeignKey(DataSet, on_delete=models.CASCADE, related_name='custom_fields')
    name = models.CharField(max_length=100, help_text="Field name (will be used as column name)")
    label = models.CharField(max_length=100, help_text="Display label for the field")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, default='text')
    required = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    help_text = models.TextField(blank=True, null=True, help_text="Help text to display to users")
    choices = models.TextField(blank=True, null=True, help_text="Comma-separated choices for choice fields")
    order = models.PositiveIntegerField(default=0, help_text="Display order (0 = first)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.label} ({self.dataset.name})"
    
    def get_choices_list(self):
        """Get choices as a list for choice fields"""
        if self.field_type == 'choice' and self.choices:
            return [choice.strip() for choice in self.choices.split(',') if choice.strip()]
        return []
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = "Custom Field"
        verbose_name_plural = "Custom Fields"
        unique_together = ['dataset', 'name']  # Field names must be unique per dataset 