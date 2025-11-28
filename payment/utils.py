
import re
import html
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.core.exceptions import ValidationError
from .exceptions import InvalidPaymentError


def validate_amount(amount_str: str) -> Decimal:
    """
    Validate and convert amount string to Decimal
    
    Args:
        amount_str: String representation of amount
        
    Returns:
        Decimal: Validated amount
        
    Raises:
        InvalidPaymentError: If amount is invalid
    """
    try:
        amount = Decimal(str(amount_str).strip())
    except (InvalidOperation, ValueError):
        raise InvalidPaymentError("Invalid amount format")
    
    # Check minimum amount
    min_amount = getattr(settings, 'PAYMENT_MIN_AMOUNT', 1)
    if amount < Decimal(str(min_amount)):
        raise InvalidPaymentError(f"Amount must be at least ₹{min_amount}")
    
    # Check maximum amount
    max_amount = getattr(settings, 'PAYMENT_MAX_AMOUNT', 100000)
    if amount > Decimal(str(max_amount)):
        raise InvalidPaymentError(f"Amount cannot exceed ₹{max_amount}")
    
    # Check decimal places
    if amount.as_tuple().exponent < -2:
        raise InvalidPaymentError("Amount cannot have more than 2 decimal places")
    
    return amount


def sanitize_user_input(user_input: str, max_length: int = 255) -> str:
    """
    Sanitize user input to prevent XSS and other attacks
    
    Args:
        user_input: Raw user input
        max_length: Maximum allowed length
        
    Returns:
        str: Sanitized input
    """
    if not user_input:
        return ""
    
    # Strip whitespace
    cleaned = str(user_input).strip()
    
    # Truncate if too long
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    # Escape HTML entities
    cleaned = html.escape(cleaned)
    
    # Remove potentially dangerous characters
    cleaned = re.sub(r'[<>"\']', '', cleaned)
    return cleaned


def validate_phone_number(phone: str) -> str:
    """
    Validate Indian phone number
    
    Args:
        phone: Phone number string
        
    Returns:
        str: Validated phone number
        
    Raises:
        InvalidPaymentError: If phone number is invalid
    """
    if not phone:
        return ""
    
    # Remove all non-digit characters
    phone_digits = re.sub(r'\D', '', phone)
    
    # Check for Indian mobile number pattern
    if len(phone_digits) == 10 and phone_digits[0] in '6789':
        return phone_digits
    elif len(phone_digits) == 13 and phone_digits.startswith('91') and phone_digits[2] in '6789':
        return phone_digits[2:]  # Remove country code
    elif len(phone_digits) == 12 and phone_digits.startswith('0') and phone_digits[1] in '6789':
        return phone_digits[1:]  # Remove leading zero
    
    raise InvalidPaymentError("Please enter a valid Indian mobile number")


def validate_email(email: str) -> str:
    """
    Basic email validation
    
    Args:
        email: Email string
        
    Returns:
        str: Validated email
        
    Raises:
        InvalidPaymentError: If email is invalid
    """
    if not email:
        return ""
    
    email = email.strip().lower()
    
    # Basic email regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        raise InvalidPaymentError("Please enter a valid email address")
    
    return email


def mask_sensitive_data(data: str, show_last: int = 4) -> str:
    """
    Mask sensitive data for logging
    
    Args:
        data: Sensitive data to mask
        show_last: Number of characters to show at the end
        
    Returns:
        str: Masked data
    """
    if not data or len(data) <= show_last:
        return '*' * len(data) if data else ''
    
    return '*' * (len(data) - show_last) + data[-show_last:]



def get_client_ip(request) -> str:
    """
    Get client IP address from request
    
    Args:
        request: Django request object
        
    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    
    return ip


def generate_payment_reference(prefix: str = "PAY") -> str:
    """
    Generate unique payment reference
    
    Args:
        prefix: Prefix for the reference
        
    Returns:
        str: Unique payment reference
    """
    import uuid
    import time
    
    timestamp = int(time.time())
    unique_id = str(uuid.uuid4())[:8].upper()
    
    return f"{prefix}_{timestamp}_{unique_id}"





import logging
from django.http import HttpResponseForbidden
from django.utils.cache import add_never_cache_headers

logger = logging.getLogger(__name__)

class PaymentSecurityMiddleware:
    """
    Security middleware for payment endpoints
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.payment_paths = ['/payment/']
    
    def __call__(self, request):
        # Add security headers for payment pages
        if any(request.path.startswith(path) for path in self.payment_paths):
            # Log payment page access
            logger.info(f"Payment page accessed: {request.path} from {get_client_ip(request)}")
            
            # Add security headers
            response = self.get_response(request)
            self.ad