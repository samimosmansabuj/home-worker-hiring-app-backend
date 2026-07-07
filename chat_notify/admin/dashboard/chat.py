from unfold.dashboard import Dashboard, DashboardItem
from chat_notify.models import ChatRoom, ChatMessage


class ChatControlDashboard(Dashboard):

    def get_items(self):

        return [

            DashboardItem(
                title="Active Chat Rooms",
                value=ChatRoom.objects.count(),
                icon="chat",
            ),

            DashboardItem(
                title="Unread Messages",
                value=ChatMessage.objects.filter(is_read=False).count(),
                icon="notification",
            ),

            DashboardItem(
                title="Today Messages",
                value=ChatMessage.objects.filter(
                    timestamp__date__today=True
                ).count(),
                icon="message",
            ),
        ]