from django.contrib.admin import TabularInline, StackedInline
from .models import Address, SavedHelper, HelperWallet, HelperWeeklyAvailability, CustomerPaymentMethod, ProviderPayoutMethod
from django.utils.html import format_html
from django.contrib import admin
from django.utils.timezone import localtime

class AddressInline(TabularInline):
    model = Address
    extra = 0

class SavedHelperInline(TabularInline):
    model = SavedHelper
    extra = 0

    fields = (
        "helper_preview",
        "created_at",
    )

    readonly_fields = (
        "helper_preview",
        "created_at",
    )
    
    @admin.display(description="Helper")
    def helper_preview(self, obj):
        user = obj.helper.user

        photo = getattr(obj.helper, "logo", None)

        img_html = ""
        if photo:
            img_html = f'<img src="{photo.url}" style="width:35px;height:35px;border-radius:50%;margin-right:10px;" />'
        else:
            img_html = "👤"

        return format_html(
            """
            <div style="display:flex;align-items:center;gap:10px;">
                {img}
                <div>
                    <div style="font-weight:600;">{name}</div>
                    <div style="font-size:12px;color:gray;">
                        {email}
                    </div>
                </div>
            </div>
            """,
            img=img_html,
            name=user.username,
            email=user.email or "No email"
        )
    

    @admin.display(description="Added At")
    def created_at(self, obj):
        return localtime(obj.created_at).strftime("%d %b %Y • %I:%M %p")


class WalletInline(StackedInline):
    model = HelperWallet
    extra = 0
    max_num = 1
    can_delete = False
    
    classes = ["collapse"]

    fieldsets = (
        ("💰 Wallet Summary", {
            "fields": (
                "available_payout",
                "upcoming_payout",
                "payout_processing",
                "total_payout",
            ),
        }),
    )

class WeeklyAvailabilityInline(TabularInline):
    model = HelperWeeklyAvailability
    extra = 0

    classes = ["collapse"]

    fields = (
        "day",
        "day_status",
        "start_time",
        "end_time",
        "slot_duration_minutes",
    )

    ordering = ("day",)


class CustomerPaymentInline(admin.TabularInline):
    model = CustomerPaymentMethod
    extra = 0
    readonly_fields = ("created_at",)

class ProviderPayoutInline(admin.TabularInline):
    model = ProviderPayoutMethod
    extra = 0
    
    classes = ["collapse"]


