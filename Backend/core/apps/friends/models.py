from django.db import models
from django.conf import settings

class Friendship(models.Model):
    STATUS_CHOICES = [
        ('none', 'None'),
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('blocked', 'Blocked'),
    ]

    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="friendship_requests_sent", on_delete=models.CASCADE)
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="friendship_requests_received", on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='none')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user} - {self.to_user} ({self.status})"
