# exceptions.py
class PaymentError(Exception):
    """Base exception for payment-related errors"""
    pass


class InvalidPaymentError(PaymentError):
    """Exception for invalid payment data"""
    pass


class PhonePeAPIError(PaymentError):
    """Exception for PhonePe API errors"""
    pass


class ChecksumVerificationError(PaymentError):
    """Exception for checksum verification failures"""
    pass

