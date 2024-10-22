from django.db import models
from core.apps.authentication.models import Player

class Friendship(models.Model):
    from_user = models.ForeignKey(Player, related_name='friendships_initiated', on_delete=models.CASCADE)
    to_user = models.ForeignKey(Player, related_name='friendships_received', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('blocked', 'Blocked')
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.status})"
