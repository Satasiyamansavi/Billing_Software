from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # 👉 username પ્રમાણે role set
        if instance.username == "Admin":
            role = "Admin"
        else:
            role = "staff"

        UserProfile.objects.create(user=instance, role=role)