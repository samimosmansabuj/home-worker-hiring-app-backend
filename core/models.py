from django.db import models
from account.models import User
from find_worker_config.model_choice import TicketStatus, TicketSenderType, TicketUserProfileType, VOUCHER_DISCOUNT_TYPE
from account.utils import generate_otp, image_delete_os, previous_image_delete_os
import random
import string


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
        if self.sender_type == TicketSenderType.ADMIN:
            self.ticket.status = TicketStatus.IN_PROGRESS
        self.ticket.save()




# Site Settings Model========================================
class SignUpSlider(models.Model):
    text = models.TextField(max_length=255)
    photo = models.ImageField(upload_to="slide/signup/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    create_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def image_update(self, instance):
        previous_image_delete_os(instance.photo, self.photo)
    
    def delete(self, *args, **kwargs):
        image_delete_os(self.photo)
        return super().delete(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        if self.pk and SignUpSlider.objects.filter(pk=self.pk).exists():
            instance = SignUpSlider.objects.get(pk=self.pk)
            self.image_update(instance)
        
        return super().save(*args, **kwargs)

class CustomerScreenSlide(models.Model):
    text = models.TextField(max_length=255)
    photo = models.ImageField(upload_to="slide/customer-screen/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    create_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def image_update(self, instance):
        previous_image_delete_os(instance.photo, self.photo)
    
    def delete(self, *args, **kwargs):
        image_delete_os(self.photo)
        return super().delete(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        if self.pk and CustomerScreenSlide.objects.filter(pk=self.pk).exists():
            instance = CustomerScreenSlide.objects.get(pk=self.pk)
            self.image_update(instance)
        
        return super().save(*args, **kwargs)


class AddOfferVoucher(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True, default="DISCOUNT VOUCHER")
    code = models.CharField(max_length=50)
    discount_type = models.CharField(max_length=20, choices=VOUCHER_DISCOUNT_TYPE.choices, default=VOUCHER_DISCOUNT_TYPE.PERCENTAGE)
    value = models.DecimalField(max_digits=10, decimal_places=2)

    minimum_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    upto_value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    is_used = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    expiry_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} for {self.name}"

    def generate_redeem_code(self):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        while Voucher.objects.filter(code=code).exists():
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return code

    def save(self, *args, **kwargs):
        if not self.code: self.code = self.generate_redeem_code()
        return super().save(*args, **kwargs)

