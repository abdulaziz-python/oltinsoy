
from django.db import models
from django.conf import settings

class Broadcast(models.Model):
    TARGET_CHOICES = (
        ('all', 'All Users'),
        ('district', 'District'),
        ('mahalla', 'Mahalla'),
    )

    title = models.CharField(max_length=255)
    message = models.TextField()
    target_type = models.CharField(max_length=20, choices=TARGET_CHOICES)
    target_id = models.IntegerField(null=True, blank=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='broadcasts_broadcasts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_count = models.IntegerField(default=0)
    read_count = models.IntegerField(default=0)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']

