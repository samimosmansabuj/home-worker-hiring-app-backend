from rest_framework import serializers
from find_worker_config.model_choice import OTPType
from django.db.models import Q
import random
import string
import secrets

def generate_otp(length=6):
    if length <= 0:
        raise ValueError("OTP length must be greater than 0")
    digits = string.digits
    otp = ''.join(secrets.choice(digits) for _ in range(length))
    return otp

def get_otp_object(data, type):
    from account.models import OTP
    otp = data.get("otp")
    email = data.get("email")
    phone = data.get("phone")
    query = Q(code=otp, is_used=False, purpose=type)
    if phone:
        query &= Q(phone=phone)
    if email:
        query &= Q(email=email)
    otp_object = OTP.objects.filter(query).last()
    if not otp_object:
        raise Exception("Invalid OTP")
    if otp_object.is_expired():
        raise Exception("OTP expired")
    otp_object.is_used = True
    otp_object.save(update_fields=["is_used"])
    return otp_object


