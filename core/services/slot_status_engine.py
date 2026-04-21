from datetime import datetime
from account.models import HelperSlotException, HelperSpecialDate, HelperWeeklyAvailability
from find_worker_config.model_choice import HelperSlotExceptionType, DayStatus, DateStatus
from task.models import Order

class SlotStatusEngine:

    def get_weekly_availability(self, provider, date_obj):
        weekday = date_obj.strftime("%a")
        availability = HelperWeeklyAvailability.objects.filter(
            provider=provider,
            day=weekday
        ).first()
        return availability
    
    # exist some issue using slot_end
    def get_special_date(self, provider, date_obj, slot_start, slot_end):
        return provider.special_dates.filter(date=date_obj, start_time__lte=slot_start.time()).first()
    
    def get_slot_exceptions(self, provider, date_obj):
        return provider.slot_exceptions.filter(date=date_obj)

    def get_booked_slots(self, provider, date_obj):
        booked_slots = []
        orders = provider.orders_as_provider.filter(working_date=date_obj)
        for order in orders:
            start_dt = datetime.combine(date_obj, order.working_start_time)
            end_dt = datetime.combine(date_obj, order.end_time)
            booked_slots.append((start_dt, end_dt))
        return booked_slots

    def combine_date_time(self, date, time):
        return datetime.combine(date, time)

    def get_status(self, provider, date_obj, slot_start, slot_end):
        now = datetime.now()
        if date_obj == now.date() and slot_start < now:
            return HelperSlotExceptionType.UNAVAILABLE
        
        weekly_availability = self.get_weekly_availability(provider=provider, date_obj=date_obj)
        if weekly_availability:
            if weekly_availability.day_status != DayStatus.AVAILABLE:
                return DayStatus.UNAVAILABLE
            if weekly_availability.start_time <= slot_start.time() and slot_end.time() <= weekly_availability.end_time:
                status = DayStatus.AVAILABLE
            else:
                status = DayStatus.UNAVAILABLE
        else:
            status = DayStatus.UNAVAILABLE
        
        special_date = self.get_special_date(provider, date_obj, slot_start, slot_end)
        if special_date:
            if special_date.date_status != DateStatus.AVAILABLE:
                return DateStatus.UNAVAILABLE
            if special_date.start_time and special_date.end_time:
                print("================================")
                print("Slot Start Time: ", slot_start)
                print("Combine Special Start Time: ", self.combine_date_time(special_date.date, special_date.start_time))
                print("--------------------------------")
                print("Slot End Time: ", slot_end)
                print("Combine Special End Time: ", self.combine_date_time(special_date.date, special_date.end_time))
                print("--------------------------------")
                print("Check Start Time: ", slot_start <= self.combine_date_time(special_date.date, special_date.start_time))
                print("Check End Time: ", slot_end <= self.combine_date_time(special_date.date, special_date.end_time))

                print("================================")


                # if special_date.start_time <= slot_start.time() and slot_end.time() <= special_date.end_time:
                if self.combine_date_time(special_date.date, special_date.start_time) <= slot_start and slot_end <= self.combine_date_time(special_date.date, special_date.end_time):
                    return DateStatus.AVAILABLE

        booked_slots = self.get_booked_slots(provider=provider, date_obj=date_obj)
        # print("booked_slots: ", booked_slots)
        if booked_slots:
            for start_dt, end_dt in booked_slots:
                if start_dt <= slot_start < end_dt:
                    return HelperSlotExceptionType.BOOKED

        slot_exceptions = self.get_slot_exceptions(provider=provider, date_obj=date_obj)
        # print("slot_exceptions: ", slot_exceptions)
        if slot_exceptions:
            for ex in slot_exceptions:
                if ex.start_time <= slot_start.time() < ex.end_time:
                    return ex.type
        
        return status