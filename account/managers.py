from django.contrib.auth.models import BaseUserManager
from find_worker_config.model_choice import UserRole

class CustomUserManager(BaseUserManager):
    def create_user(self, phone, email, username, password=None, **extra_fields):
        if not phone:
            raise ValueError("Phone number is required")
        if not email:
            raise ValueError("Email is required")
        user = self.model(
            phone=phone,
            email=email,
            username=username,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone, email, username, password, **extra_fields):
        extra_fields.setdefault("role", UserRole.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(phone, email, username, password, **extra_fields)
