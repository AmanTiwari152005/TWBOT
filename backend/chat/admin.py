from django.contrib import admin

from .models import ChatMessage, UserLead


@admin.register(UserLead)
class UserLeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'business_type', 'lead_completed', 'email_sent', 'last_activity', 'created_at')
    search_fields = ('name', 'phone', 'business_type', 'session_id')
    readonly_fields = ('created_at', 'last_activity', 'email_sent_at', 'lead_notification_sent_at')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__name', 'user_message', 'bot_response')
    readonly_fields = ('created_at',)
