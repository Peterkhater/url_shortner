from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Link(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='links')
    original = models.TextField(null=False, blank=False)
    short_code = models.TextField(null=False, blank=False)  # Ensure short_code is unique
    date_created = models.DateField(auto_now=True)

    def __str__(self):
        return self.original


class Profile(models.Model):
    USER_SUB_STATUS = [
        ('trial', 'Trial'),
        ('premium', 'Premium'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    sub_status = models.CharField(max_length=25, choices=USER_SUB_STATUS, default='trial')
    telegram_user_id = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"Profile('{self.user.username}', '{self.sub_status}', '{self.telegram_user_id}')"


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.profile.save()
