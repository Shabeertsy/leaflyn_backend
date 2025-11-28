import random
import string
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import OTP


def generate_otp(length=6):
    """Generate a random OTP code"""
    return ''.join(random.choices(string.digits, k=length))


def create_otp(contact, contact_type, expiry_minutes=5):
    """
    Create and save an OTP for the given contact
    
    Args:
        contact: Email or phone number
        contact_type: 'email' or 'phone'
        expiry_minutes: OTP validity duration in minutes
    
    Returns:
        OTP instance
    """
    # Deactivate any existing active OTPs for this contact
    OTP.objects.filter(
        contact=contact,
        is_verified=False,
        active_status=True
    ).update(active_status=False)
    
    otp_code = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=expiry_minutes)
    
    otp = OTP.objects.create(
        contact=contact,
        otp_code=otp_code,
        contact_type=contact_type,
        expires_at=expires_at
    )
    
    return otp


def send_otp_email(email, otp_code):
    """Send OTP via email"""
    subject = 'Your OTP Code - Leafin'
    message = f"""
    Hello,
    
    Your OTP code is: {otp_code}
    
    This code will expire in 5 minutes.
    
    If you didn't request this code, please ignore this email.
    
    Best regards,
    Leafin Team
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@leafin.com',
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def send_otp_sms(phone_number, otp_code):
    """
    Send OTP via SMS
    
    Note: This is a placeholder. You'll need to integrate with an SMS provider
    like Twilio, AWS SNS, or any other SMS gateway service.
    """
    # TODO: Integrate with SMS provider
    # Example with Twilio:
    # from twilio.rest import Client
    # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    # message = client.messages.create(
    #     body=f"Your Leafin OTP code is: {otp_code}. Valid for 5 minutes.",
    #     from_=settings.TWILIO_PHONE_NUMBER,
    #     to=phone_number
    # )
    
    # For development, just print the OTP
    print(f"SMS OTP for {phone_number}: {otp_code}")
    return True


def verify_otp(contact, otp_code):
    """
    Verify the OTP code for a given contact
    
    Args:
        contact: Email or phone number
        otp_code: The OTP code to verify
    
    Returns:
        tuple: (success: bool, message: str, otp: OTP or None)
    """
    try:
        otp = OTP.objects.filter(
            contact=contact,
            otp_code=otp_code,
            is_verified=False,
            active_status=True
        ).latest('created_at')
        
        if otp.is_expired():
            return False, "OTP has expired", None
        
        # Mark as verified
        otp.is_verified = True
        otp.save()
        
        return True, "OTP verified successfully", otp
        
    except OTP.DoesNotExist:
        return False, "Invalid OTP code", None


def resend_otp(contact, contact_type):
    """
    Resend OTP to the contact
    
    Args:
        contact: Email or phone number
        contact_type: 'email' or 'phone'
    
    Returns:
        tuple: (success: bool, message: str)
    """
    # Create new OTP
    otp = create_otp(contact, contact_type)
    
    # Send OTP based on contact type
    if contact_type == 'email':
        success = send_otp_email(contact, otp.otp_code)
        return success, "OTP sent to email" if success else "Failed to send email"
    else:  # phone
        success = send_otp_sms(contact, otp.otp_code)
        return success, "OTP sent to phone" if success else "Failed to send SMS"
