from django.db import models
from core.apps.authentication.models import Player

class Message(models.Model):
    sender = models.ForeignKey(Player, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(Player, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('timestamp',)

    def __str__(self):
        return f'{self.sender} -> {self.receiver}: {self.content[:20]}'
