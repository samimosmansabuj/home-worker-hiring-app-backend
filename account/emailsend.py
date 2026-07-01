from core.models import EmailConfig
from django.core.mail import EmailMessage, get_connection
from django.conf import settings
from rest_framework.response import Response
from django.template.loader import render_to_string

# def LogInOTPSend(otp_object):
def EmailOTPSend(otp_object):
    email_config = EmailConfig.objects.filter(is_active=True).first()
    if not email_config:
        raise Exception("No active email configuration found.")
    
    email = otp_object.email
    otp = otp_object.code
    
    subject = "Your OTP Code for Home Worker APP"
    context = {"otp": otp}
    html_message = render_to_string(
        "mail_template/otp_send.html",
        context,
    )
       
    connection = get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=email_config.host,
        port=int(email_config.port),
        username=email_config.host_user,
        password=email_config.host_password,
        use_tls=email_config.tls,
        fail_silently=False,
    )
    email_message = EmailMessage(
        subject=subject,
        body=html_message,
        from_email=f"{email_config.name} <{email_config.email}>",
        to=[email],
        connection=connection,
    )
    email_message.content_subtype = "html"

    try:
        email_message.send()
        print(
            f"[OTP] Successfully sent OTP "
            f"{otp} to {email}"
        )
        return True
    except Exception as e:
        print(
            f"[OTP] Failed to send OTP "
            f"to {email}: {str(e)}"
        )
        raise Exception(
            f"Failed to send OTP: {str(e)}"
        )


