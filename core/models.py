from django.db import models
from account.models import User
from find_worker_config.model_choice import TicketStatus, TicketSenderType, TicketUserProfileType


class Ticket(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="tickets")
    user_profile_type = models.CharField(max_length=50, choices=TicketUserProfileType.choices, blank=True, null=True)
    subject = models.CharField(max_length=255)
    order = models.ForeignKey("task.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets")
    status = models.CharField(max_length=20, choices=TicketStatus.choices, default=TicketStatus.OPEN)
    summary = models.TextField(blank=True, null=True)
    attachment = models.FileField(upload_to="tickets/", blank=True, null=True)

    last_message = models.TextField(blank=True, null=True)
    last_reply_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.subject} ({self.user})"


class TicketReply(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="replies")
    reply_sender = models.ForeignKey(User, on_delete=models.CASCADE)
    sender_type = models.CharField(max_length=20, choices=TicketSenderType.choices)
    message = models.TextField()
    attachment = models.FileField(upload_to="ticket_replies/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.ticket.last_message = self.message
        self.ticket.last_reply_at = self.created_at
        if self.sender_type == self.SenderType.ADMIN:
            self.ticket.status = Ticket.Status.IN_PROGRESS
        self.ticket.save()

