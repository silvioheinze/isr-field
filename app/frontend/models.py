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