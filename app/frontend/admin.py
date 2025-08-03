from django.contrib import admin
from .models import AuditLog, DataSet
 
admin.site.register(AuditLog)
admin.site.register(DataSet) 