from django.contrib import admin
from .models import AuditLog, DataSet, DataGeometry, DataEntry, DataEntryFile, MappingArea
 
admin.site.register(AuditLog)
admin.site.register(DataSet)
admin.site.register(DataGeometry)
admin.site.register(DataEntry)
admin.site.register(DataEntryFile)


@admin.register(MappingArea)
class MappingAreaAdmin(admin.ModelAdmin):
    list_display = ['name', 'dataset', 'created_by', 'created_at', 'get_point_count']
    list_filter = ['dataset', 'created_at']
    search_fields = ['name', 'dataset__name', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['allocated_users']
    
    def get_point_count(self, obj):
        return obj.get_point_count()
    get_point_count.short_description = 'Points Inside' 