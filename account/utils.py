import random
import string
import secrets

def generate_otp(length=6):
    if length <= 0:
        raise ValueError("OTP length must be greater than 0")
    digits = string.digits
    otp = ''.join(secrets.choice(digits) for _ in range(length))
    return otp





