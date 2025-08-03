from django.contrib import admin
from .models import AuditLog, DataSet, DataGeometry
 
admin.site.register(AuditLog)
admin.site.register(DataSet)
admin.site.register(DataGeometry) 