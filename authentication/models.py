from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid


class BaseModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active_status = models.BooleanField(default=True)
    deleted_at=models.DateTimeField(null=True,blank=True)


    class Meta:
        abstract = True


class CustomUserManager(BaseUserManager):
    def create_user(self, email=None, phone_number=None, password=None, **extra_fields):
        if not email and not phone_number:
            raise ValueError('Either Email or Phone Number must be set')
        
        if email:
            email = self.normalize_email(email)
        
        user = self.model(email=email, phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'admin')

        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        return self.create_user(email=email, password=password, **extra_fields)


class Profile(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, blank=True, null=True)
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)  # Track if phone/email is verified
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    user_type = models.CharField(
        max_length=10,
        choices=[('admin', 'Admin'), ('user', 'User')],
        default='user'
    )
    bio = models.TextField(blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email or self.phone_number or 'No identifier'

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        if full_name:
            return full_name
        if hasattr(self, 'username') and self.username:
            return self.username
        return 'No name'

    def get_username(self):
        if hasattr(self, 'username') and self.username:
            return self.username
        return self.email or self.phone_number or 'Unknown'
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(email__isnull=False) | models.Q(phone_number__isnull=False),
                name='email_or_phone_required'
            )
        ]


class OTP(BaseModel):
    """Model to store OTP codes for authentication"""
    contact = models.CharField(max_length=255)  # Can be email or phone number
    otp_code = models.CharField(max_length=6)
    contact_type = models.CharField(
        max_length=10,
        choices=[('email', 'Email'), ('phone', 'Phone')],
    )
    is_verified = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['contact', 'otp_code']),
        ]
    
    def __str__(self):
        return f"OTP for {self.contact} - {self.otp_code}"
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
