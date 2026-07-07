from django.contrib import admin
from .models import Ticket, TicketReply, AddOfferVoucher, AdminWallet, SignUpSlider, CustomerScreenSlide, EmailConfig
from unfold.admin import ModelAdmin

@admin.register(Ticket)
class TicketAdmin(ModelAdmin):
    list_display = (
        "id",
        "subject",
        "user",
        "status",
        "order_id",
        "last_reply_at",
        "created_at",
    )

    search_fields = (
        "subject",
        "user__username",
        "order__id",
    )

    list_filter = (
        "status",
        "created_at",
        "user_profile_type",
    )

    readonly_fields = (
        "last_message",
        "last_reply_at",
        "created_at",
        "updated_at",
    )

    date_hierarchy = "created_at"

    fieldsets = (
        ("Ticket Info", {
            "fields": (
                "user",
                "user_profile_type",
                "subject",
                "order",
                "status",
            )
        }),

        ("Summary", {
            "fields": (
                "summary",
                "attachment",
            )
        }),

        ("Activity", {
            "fields": (
                "last_message",
                "last_reply_at",
            )
        }),

        ("System", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    def order_id(self, obj):
        return obj.order.id if obj.order else "-"

@admin.register(TicketReply)
class TicketReplyAdmin(ModelAdmin):
    list_display = (
        "ticket",
        "reply_sender",
        "sender_type",
        "short_message",
        "created_at",
    )

    search_fields = (
        "message",
        "ticket__subject",
    )

    list_filter = (
        "sender_type",
        "created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = ("created_at",)

    def short_message(self, obj):
        return obj.message[:60]

@admin.register(SignUpSlider)
class SignUpSliderAdmin(ModelAdmin):
    list_display = (
        "id",
        "text",
        "is_active",
        "create_at",
    )

    list_filter = ("is_active",)
    search_fields = ("text",)
    readonly_fields = ("create_at", "updated_at")

@admin.register(CustomerScreenSlide)
class CustomerScreenSlideAdmin(ModelAdmin):
    list_display = (
        "id",
        "text",
        "is_active",
        "create_at",
    )

    list_filter = ("is_active",)
    search_fields = ("text",)
    readonly_fields = ("create_at", "updated_at")

@admin.register(AddOfferVoucher)
class AddOfferVoucherAdmin(ModelAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "value",
        "is_used",
        "is_active",
        "expiry_date",
    )

    search_fields = ("code", "name")
    readonly_fields = ("created_at",)

    list_filter = (
        "is_used",
        "is_active",
        "discount_type",
    )

    fieldsets = (
        ("Voucher Info", {
            "fields": (
                "name",
                "code",
            )
        }),

        ("Discount", {
            "fields": (
                "discount_type",
                "value",
                "minimum_value",
                "upto_value",
            )
        }),

        ("Status", {
            "fields": (
                "is_used",
                "is_active",
                "expiry_date",
            )
        }),
    )

@admin.register(AdminWallet)
class AdminWalletAdmin(ModelAdmin):
    list_display = (
        "current_balance",
        "payment_balance",
        "hold_balance",
        "total_withdraw",
        "update_at",
    )

    readonly_fields = (
        "created_at",
        "update_at",
    )

    fieldsets = (
        ("Balance Overview", {
            "fields": (
                "current_balance",
                "payment_balance",
                "hold_balance",
                "total_withdraw",
            )
        }),

        ("System Info", {
            "fields": (
                "created_at",
                "update_at",
            )
        }),
    )

@admin.register(EmailConfig)
class EmailConfigAdmin(ModelAdmin):
    list_display = ("name", "email", "type", "host", "port", "is_default", "is_active", "today_count", "daily_limit", "today_complete")

    list_filter = ("type", "is_default", "is_active", "tls", "ssl", "today_complete")

    search_fields = ("name", "email", "host", "host_user")

    readonly_fields = ("today_count", "today_date", "today_complete")

    fieldsets = (
        ("Email Configuration", {"fields": ("type", "name", "email", "is_default", "is_active")}),
        ("SMTP Settings", {"fields": ("host", "port", "host_user", "host_password", "tls", "ssl")}),
        ("API Configuration", {"fields": ("server", "api_key")}),
        ("Daily Limit", {"fields": ("daily_limit", "today_count", "today_date", "today_complete")}),
    )

