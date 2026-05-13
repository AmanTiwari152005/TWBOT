from django.contrib import admin

from .models import ChatMessage, UserLead


@admin.register(UserLead)
class UserLeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'business_type', 'created_at')
    search_fields = ('name', 'business_type')
    readonly_fields = ('created_at',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__name', 'user_message', 'bot_response')
    readonly_fields = ('created_at',)
