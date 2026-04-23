from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ActivityLog, ServiceProviderProfile, ProviderVerification
from chat_notify.models import Notification
from chat_notify.utils import push_notification

@receiver(post_save, sender=ActivityLog)
def create_log_notification(sender, instance, created, **kwargs):
    if created and instance.need_notify:
        notification = Notification.objects.create(
            received=instance.user,
            profile=instance.user_type,
            action=instance.action,
            entity_type=instance.entity_type,
            entity_id=instance.entity_id,
            metadata=instance.metadata,
        )
        push_notification(
            user_id=notification.received.id,
            data={
                "notify_text": notification.notify_text,
                "entity_type": "order",
                "entity": notification.entity_id,
                "is_read": notification.is_read
            }
        )
        return notification


@receiver(post_save, sender=ServiceProviderProfile)
def create_provider_verification_object(sender, instance, created, **kwargs):
    if created or not hasattr(instance, "verification"):
        ProviderVerification.objects.create(
            provider=instance
        )
        return True

