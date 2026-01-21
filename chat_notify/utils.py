from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def push_notification(user_id, data):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"notify_{user_id}",
        {
            "type": "notify",
            "data": data
        }
    )

def push_notify_role(role, data):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"role_{role}",
        {
            "type": "notify",
            "data": data
        }
    )

def push_notify_all(data):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "notify_all",
        {
            "type": "notify",
            "data": data
        }
    )
