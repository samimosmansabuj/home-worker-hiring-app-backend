from django.contrib import admin
# from .models import ServiceCategory, ServiceTask, ServicePrototype, TaskRequest
from .models import ServiceCategory, Order, ReviewAndRating, AdminWallet, PaymentTransaction, OrderRefundRequest, OrderChangesRequest
from unfold.admin import ModelAdmin

# @admin.register(Order)
# class OrderAdmin(ModelAdmin):
#     list_display = (
#         "id", "customer", "provider",
#         "status", "payment_status", "amount", "created_at"
#     )

#     list_filter = ("status", "payment_status")
#     search_fields = ("id", "customer__user__email")

#     list_select_related = ("customer", "provider")

#     readonly_fields = ("accepted_at", "completed_at")

#     actions = ["mark_completed"]

#     @admin.action(description="Mark as Completed")
#     def mark_completed(self, request, queryset):
#         queryset.update(status="completed")

admin.site.register(ServiceCategory)
admin.site.register(Order)
admin.site.register(OrderChangesRequest)
admin.site.register(ReviewAndRating)
admin.site.register(AdminWallet)
admin.site.register(PaymentTransaction)
admin.site.register(OrderRefundRequest)

