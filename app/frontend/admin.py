from django.contrib import admin
from .models import AuditLog, DataSet, DataGeometry, DataEntry
 
admin.site.register(AuditLog)
admin.site.register(DataSet)
admin.site.register(DataGeometry)
admin.site.register(DataEntry) 