
from django.contrib import admin
from .models import Broadcast

@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ('title', 'target_type', 'sent_by', 'created_at', 'delivered_count', 'read_count')
    list_filter = ('target_type', 'created_at')
    search_fields = ('title', 'message')
    readonly_fields = ('delivered_count', 'read_count')
    date_hierarchy = 'created_at'

