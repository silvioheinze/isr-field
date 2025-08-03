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