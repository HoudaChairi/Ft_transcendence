from django.contrib import admin
from .models import Message

class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'content_snippet', 'timestamp')
    search_fields = ('sender__username', 'receiver__username', 'content')
    list_filter = ('sender', 'receiver', 'timestamp')
    ordering = ('-timestamp',)

    def content_snippet(self, obj):
        return obj.content[:50]
    content_snippet.short_description = 'Message Content'

admin.site.register(Message, MessageAdmin)
