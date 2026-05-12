from django.contrib import admin
from .models import Ticket, TicketReply, AddOfferVoucher
# from unfold.admin import ModelAdmin



# @admin.register(Ticket)
# class TicketAdmin(ModelAdmin):
#     list_display = ("id", "user", "status", "subject", "last_reply_at")
#     list_filter = ("status",)

#     search_fields = ("subject", "user__email")

#     actions = ["mark_resolved"]

#     @admin.action(description="Mark as resolved")
#     def mark_resolved(self, request, queryset):
#         queryset.update(status="closed")

admin.site.register(Ticket)
admin.site.register(TicketReply)
admin.site.register(AddOfferVoucher)
