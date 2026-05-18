from django.db import models
from django.utils import timezone


class UserLead(models.Model):
    session_id = models.CharField(max_length=80, blank=True, null=True, unique=True)
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=40, blank=True)
    business_type = models.CharField(max_length=160)
    email_sent = models.BooleanField(default=False)
    lead_completed = models.BooleanField(default=False)
    lead_notification_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(blank=True, null=True)
    lead_notification_sent_at = models.DateTimeField(blank=True, null=True)
    last_activity = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} - {self.phone or self.business_type}'


class ChatMessage(models.Model):
    user = models.ForeignKey(UserLead, on_delete=models.CASCADE, related_name='messages')
    user_message = models.TextField()
    bot_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Chat with {self.user.name} at {self.created_at:%Y-%m-%d %H:%M}'
