from datetime import datetime, timedelta
from account.models import HelperWeeklyAvailability
from find_worker_config.model_choice import HelperSlotExceptionType, DayStatus, DateStatus, OrderStatus
from django.db.models import Case, When, IntegerField

class SlotStatusEngine:

    def get_weekly_availability(self, provider, date_obj):
        weekday = date_obj.strftime("%a")
        availability = HelperWeeklyAvailability.objects.filter(
            provider=provider,
            day=weekday
        ).first()
        return availability
    
    # exist some issue using slot_end
    def get_special_date(self, provider, date_obj):
        return provider.special_dates.filter(date=date_obj).first()
    
    def get_slot_exceptions(self, provider, date_obj):
        # return provider.slot_exceptions.filter(date=date_obj)
        return provider.slot_exceptions.filter(
            date=date_obj
        ).annotate(
            priority=Case(
                When(type="BOOKED", then=0),
                When(type="FREEZED", then=1),
                default=2,
                output_field=IntegerField()
            )
        ).order_by("priority", "-created_at")

    def get_booked_slots(self, provider, date_obj):
        booked_slots = []
        orders = provider.orders_as_provider.filter(working_date=date_obj, status__in=[OrderStatus.ACCEPT, OrderStatus.CONFIRM, OrderStatus.IN_PROGRESS])
        for order in orders:
            if order.working_start_time and order.working_hour:
                start_dt = datetime.combine(date_obj, order.working_start_time)
                end_dt = order.end_datetime
                booked_slots.append((start_dt, end_dt))
        return booked_slots

    def combine_date_time(self, date, time):
        return datetime.combine(date, time)

    def get_status(self, provider, date_obj, slot_start, slot_end):
        # print(f"date: {date_obj}, slot_start: {slot_start}, slot_end: {slot_end}")
        now = datetime.now()
        if date_obj == now.date() and slot_start < now:
            return HelperSlotExceptionType.UNAVAILABLE
        
        weekly_availability = self.get_weekly_availability(provider=provider, date_obj=date_obj)
        if weekly_availability:
            if weekly_availability.day_status != DayStatus.AVAILABLE:
                status = DayStatus.UNAVAILABLE
            if self.combine_date_time(date_obj, weekly_availability.start_time) <= slot_start and slot_end <= self.combine_date_time(date_obj, weekly_availability.end_time):
                status = DayStatus.AVAILABLE
            else:
                status = DayStatus.UNAVAILABLE
        else:
            status = DayStatus.UNAVAILABLE

        special_date = self.get_special_date(provider, date_obj)
        if special_date:
            if special_date.date_status != DateStatus.AVAILABLE:
                status = DateStatus.UNAVAILABLE
            if special_date.start_time and special_date.end_time:
                if slot_start >= self.combine_date_time(special_date.date, special_date.start_time) and slot_end <= self.combine_date_time(special_date.date, special_date.end_time):
                    status = DateStatus.AVAILABLE
        
        slot_exceptions = self.get_slot_exceptions(provider=provider, date_obj=date_obj)
        if slot_exceptions:
            for ex in slot_exceptions:
                if ex.start_time <= slot_start.time() < ex.end_time:
                    return ex.type
        
        # booked_slots = self.get_booked_slots(provider=provider, date_obj=date_obj)
        # if booked_slots:
        #     for start_dt, end_dt in booked_slots:
        #         if start_dt <= slot_start < end_dt:
        #             return HelperSlotExceptionType.BOOKED
        
        return status