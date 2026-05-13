from django.db import models


class UserLead(models.Model):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=40, blank=True)
    business_type = models.CharField(max_length=160)
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
