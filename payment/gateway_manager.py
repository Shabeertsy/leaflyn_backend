import logging
from decimal import Decimal
from typing import Optional, Dict, Any
from django.core.exceptions import ValidationError
from .models import PaymentGateway, PaymentGatewayLog

logger = logging.getLogger(__name__)


class PaymentGatewayManager:
    """Manages multiple payment gateways"""
    
    @staticmethod
    def get_active_gateways():
        """Get all active payment gateways"""
        return PaymentGateway.objects.filter(is_active=True).order_by('priority')
    
    @staticmethod
    def get_default_gateway() -> Optional[PaymentGateway]:
        """Get the default payment gateway"""
        try:
            return PaymentGateway.objects.get(is_default=True, is_active=True)
        except PaymentGateway.DoesNotExist:
            return PaymentGateway.objects.filter(is_active=True).order_by('priority').first()
    
    @staticmethod
    def get_gateway_by_name(name: str) -> Optional[PaymentGateway]:
        """Get gateway by name"""
        try:
            return PaymentGateway.objects.get(name=name, is_active=True)
        except PaymentGateway.DoesNotExist:
            return None
    
    @staticmethod
    def get_suitable_gateway(amount: Decimal, gateway_name: Optional[str] = None) -> PaymentGateway:
        """
        Get a suitable gateway for the given amount
        If gateway_name is provided, use that gateway
        Otherwise, use default gateway
        """
        if gateway_name:
            gateway = PaymentGatewayManager.get_gateway_by_name(gateway_name)
            if not gateway:
                raise ValidationError(f"Gateway '{gateway_name}' not found or inactive")
        else:
            gateway = PaymentGatewayManager.get_default_gateway()
            if not gateway:
                raise ValidationError("No active payment gateway available")
        
        # Validate amount
        if not gateway.is_amount_valid(amount):
            raise ValidationError(
                f"Amount must be between ₹{gateway.min_amount} and "
                f"₹{gateway.max_amount or 'unlimited'}"
            )
        
        return gateway
    
    @staticmethod
    def log_gateway_action(gateway: PaymentGateway, action: str, 
                          request_data: Dict = None, response_data: Dict = None,
                          status: str = 'success', error_message: str = '',
                          payment=None, ip_address: str = None, 
                          user_agent: str = ''):
        """Log gateway actions"""
        try:
            PaymentGatewayLog.objects.create(
                gateway=gateway,
                payment=payment,
                action=action,
                request_data=request_data,
                response_data=response_data,
                status=status,
                error_message=error_message,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as e:
            logger.error(f"Failed to log gateway action: {e}")


class GatewayClientFactory:
    """Factory to create gateway-specific clients"""
    
    @staticmethod
    def get_client(gateway: PaymentGateway):
        """Get the appropriate gateway client"""
        if gateway.name == 'phonepe':
            return PhonePeGatewayClient(gateway)
        elif gateway.name == 'razorpay':
            return RazorpayGatewayClient(gateway)
        elif gateway.name == 'stripe':
            return StripeGatewayClient(gateway)
        elif gateway.name == 'paytm':
            return PaytmGatewayClient(gateway)
        elif gateway.name == 'cashfree':
            return CashfreeGatewayClient(gateway)
        else:
            raise ValidationError(f"Unsupported gateway: {gateway.name}")


class BaseGatewayClient:
    """Base class for all gateway clients"""
    
    def __init__(self, gateway: PaymentGateway):
        self.gateway = gateway
        self.credentials = gateway.credentials
        self.config = gateway.configuration
        self.is_production = gateway.environment == 'production'
    
    def initiate_payment(self, payment, redirect_url: str) -> Dict[str, Any]:
        """Initiate payment - must be implemented by subclass"""
        raise NotImplementedError
    
    def check_status(self, merchant_transaction_id: str) -> Dict[str, Any]:
        """Check payment status - must be implemented by subclass"""
        raise NotImplementedError
    
    def process_webhook(self, request) -> Dict[str, Any]:
        """Process webhook - must be implemented by subclass"""
        raise NotImplementedError
    
    def initiate_refund(self, payment, amount: Decimal) -> Dict[str, Any]:
        """Initiate refund - must be implemented by subclass"""
        raise NotImplementedError


class PhonePeGatewayClient(BaseGatewayClient):
    """PhonePe specific implementation"""

    def __init__(self, gateway: PaymentGateway):
        super().__init__(gateway)
        self._setup_client()

    def _setup_client(self):
        """Setup PhonePe client"""
        from phonepe.sdk.pg.env import Env
        from phonepe.sdk.pg.payments.v2.standard_checkout_client import StandardCheckoutClient

        env = Env.PRODUCTION if self.is_production else Env.SANDBOX

        self.client = StandardCheckoutClient.get_instance(
            client_id=self.credentials.get('client_id'),
            client_secret=self.credentials.get('client_secret'),
            client_version=self.credentials.get('client_version', 1),
            env=env,
            should_publish_events=False
        )

    def initiate_payment(self, payment, redirect_url: str) -> Dict[str, Any]:
        """Initiate PhonePe payment"""
        from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import StandardCheckoutPayRequest
        from phonepe.sdk.pg.common.models.request.meta_info import MetaInfo

        try:
            meta_info = MetaInfo(
                udf1=payment.payment_metadata.get('description', 'Payment')[:100]
            )

            pay_request = StandardCheckoutPayRequest.build_request(
                merchant_order_id=payment.merchant_transaction_id,
                amount=int(payment.amount * 100),
                redirect_url=redirect_url,
                meta_info=meta_info,
            )

            response = self.client.pay(pay_request)

            PaymentGatewayManager.log_gateway_action(
                gateway=self.gateway,
                action='payment_initiated',
                request_data={'amount': str(payment.amount)},
                response_data={'redirect_url': getattr(response, 'redirect_url', None)},
                status='success',
                payment=payment
            )

            return {
                'success': True,
                'redirect_url': getattr(response, 'redirect_url', None),
                'transaction_id': payment.merchant_transaction_id
            }

        except Exception as e:
            PaymentGatewayManager.log_gateway_action(
                gateway=self.gateway,
                action='payment_initiation_failed',
                status='failed',
                error_message=str(e),
                payment=payment
            )
            raise

    def check_status(self, merchant_transaction_id: str) -> Dict[str, Any]:
        """Check PhonePe payment status"""
        try:
            response = self.client.get_order_status(merchant_transaction_id, details=True)
            return {
                'success': True,
                'status': str(getattr(response, 'state', '')).lower(),
                'response': response
            }
        except Exception as e:
            logger.error(f"PhonePe status check failed: {e}")
            raise

    def process_webhook(self, request) -> Dict[str, Any]:
        """
        Process PhonePe webhook using the PhonePe SDK for validation.
        Expected: request to be a Django request object.
        Returns: Dict with result status.
        """
        import time

        try:
            webhook_start_time = time.time()
            client_ip = getattr(request, "META", {}).get("REMOTE_ADDR", "")

            raw_body = request.body.decode("utf-8")
            authorization_header = request.headers.get('Authorization', '')

            if not raw_body or not authorization_header:
                logger.error("PhonePe webhook: Missing raw body or authorization header")
                return {"error": "Missing required data", "success": False}

            import os
            from django.conf import settings
            from phonepe.sdk.pg.common.exceptions import PhonePeException

            username = (
                os.environ.get('PHONEPE_WEBHOOK_USERNAME') or
                getattr(settings, 'PHONEPE_WEBHOOK_USERNAME', '')
            )
            password = (
                os.environ.get('PHONEPE_WEBHOOK_PASSWORD') or
                getattr(settings, 'PHONEPE_WEBHOOK_PASSWORD', '')
            )

            if not username or not password:
                logger.error("PhonePe webhook: Missing webhook validation credentials")
                return {"error": "Missing webhook credentials", "success": False}

            callback_response = None
            try:
                callback_response = self.client.validate_callback(
                    username=username,
                    password=password,
                    callback_header_data=authorization_header,
                    callback_response_data=raw_body
                )
            except PhonePeException as sdk_err:
                logger.error(f"PhonePe SDK webhook validation error: {sdk_err.code} - {sdk_err.message}")
                return {"error": "PhonePe SDK validation failed", "success": False}

            if not callback_response or not hasattr(callback_response, "type"):
                logger.warning("PhonePe webhook: Validation failed or missing type")
                return {"error": "Webhook validation failed", "success": False}

            callback_type = callback_response.type
            payload = getattr(callback_response, "payload", None)

            # PAYMENT
            if callback_type in ['CHECKOUT_ORDER_COMPLETED', 'CHECKOUT_ORDER_FAILED']:
                merchant_transaction_id = getattr(payload, 'original_merchant_order_id', None)
                phonepe_order_id = getattr(payload, 'order_id', None)
                payment_state = getattr(payload, 'state', None)
                amount = getattr(payload, 'amount', None)

                if not merchant_transaction_id or not payment_state:
                    return {"error": "Missing required fields", "success": False}

                from .models import Payment, PaymentLog
                try:
                    payment = Payment.objects.get(merchant_transaction_id=merchant_transaction_id)
                except Payment.DoesNotExist:
                    logger.error(f"PhonePe webhook: Payment not found for transaction {merchant_transaction_id}")
                    return {"error": "Payment not found", "success": False}

                if callback_type == 'CHECKOUT_ORDER_COMPLETED' and str(payment_state).upper() == 'COMPLETED':
                    new_status = 'completed'
                elif callback_type == 'CHECKOUT_ORDER_FAILED' or str(payment_state).upper() == 'FAILED':
                    new_status = 'failed'
                else:
                    new_status = 'pending'

                old_status = payment.status

                from .views import PaymentManager
                gateway_data = {
                    'callback_type': callback_type,
                    'state': payment_state,
                    'phonepe_order_id': phonepe_order_id,
                    'amount': amount,
                    'merchant_id': getattr(payload, 'merchant_id', ''),
                    'webhook_timestamp': time.time()
                }
                payment_details = getattr(payload, 'payment_details', None)
                if payment_details and len(payment_details) > 0:
                    payment_detail = payment_details[0]
                    gateway_data.update({
                        'transaction_id': getattr(payment_detail, 'transaction_id', ''),
                        'payment_mode': getattr(payment_detail, 'payment_mode', ''),
                        'payment_timestamp': getattr(payment_detail, 'timestamp', '')
                    })

                if new_status == 'failed':
                    gateway_data.update({
                        'error_code': getattr(payload, 'error_code', ''),
                        'detailed_error_code': getattr(payload, 'detailed_error_code', '')
                    })

                expire_at = getattr(payload, 'expire_at', None)
                if expire_at:
                    gateway_data['expire_at'] = expire_at

                if old_status != new_status:
                    PaymentManager.update_payment_status(
                        payment=payment,
                        status=new_status,
                        gateway_data=gateway_data,
                        phonepe_transaction_id=gateway_data.get('transaction_id', '')
                    )
                processing_time = (time.time() - webhook_start_time) * 1000
                PaymentLog.log_payment_event(
                    payment=payment,
                    action='payment_callback_processed',
                    details={
                        'callback_type': callback_type,
                        'payment_state': payment_state,
                        'phonepe_order_id': phonepe_order_id,
                        'status_changed': old_status != new_status,
                        'processing_time_ms': round(processing_time, 2),
                        'webhook_ip': client_ip
                    },
                    ip_address=client_ip
                )
                return {
                    "success": True,
                    "status": "processed",
                    "payment_status": new_status,
                    "processing_time_ms": round(processing_time, 2)
                }

            # REFUND
            elif callback_type in ['PG_REFUND_COMPLETED', 'PG_REFUND_FAILED', 'PG_REFUND_ACCEPTED']:
                merchant_refund_id = getattr(payload, 'merchant_refund_id', None)
                phonepe_refund_id = getattr(payload, 'refund_id', None)
                refund_state = getattr(payload, 'state', None)
                amount = getattr(payload, 'amount', None)
                processing_time = (time.time() - webhook_start_time) * 1000
                logger.info(f"PhonePe refund webhook: {merchant_refund_id} -> {refund_state}")
                return {
                    "success": True,
                    "status": "refund_callback_processed",
                    "refund_status": refund_state,
                    "processing_time_ms": round(processing_time, 2)
                }
            else:
                logger.info(f"PhonePe webhook: Unknown callback type {callback_type}")
                return {
                    "success": True,
                    "message": "Unknown callback type processed"
                }

        except Exception as e:
            logger.exception("PhonePe webhook critical error")
            return {"error": str(e), "success": False}

    def initiate_refund(self, payment, amount: Decimal) -> Dict[str, Any]:
        """
        Initiate a refund for a PhonePe payment.
        """
        from phonepe.sdk.pg.payments.v1.refund_client import RefundClient
        import uuid

        try:
            refund_client = RefundClient(self.client)
            merchant_refund_id = str(uuid.uuid4())

            refund_response = refund_client.initiate_refund(
                merchant_order_id=payment.merchant_transaction_id,
                amount=int(amount * 100),
                merchant_refund_id=merchant_refund_id
            )

            PaymentGatewayManager.log_gateway_action(
                gateway=self.gateway,
                action='refund_initiated',
                request_data={
                    'merchant_order_id': payment.merchant_transaction_id,
                    'amount': str(amount),
                    'merchant_refund_id': merchant_refund_id
                },
                response_data={'refund_id': getattr(refund_response, 'refund_id', None)},
                status='success',
                payment=payment,
            )

            return {
                "success": True,
                "merchant_refund_id": merchant_refund_id,
                "refund_id": getattr(refund_response, 'refund_id', None),
                "refund_response": refund_response
            }

        except Exception as e:
            PaymentGatewayManager.log_gateway_action(
                gateway=self.gateway,
                action='refund_initiation_failed',
                request_data={
                    'merchant_order_id': payment.merchant_transaction_id,
                    'amount': str(amount)
                },
                status='failed',
                error_message=str(e),
                payment=payment,
            )
            raise



class RazorpayGatewayClient(BaseGatewayClient):
    """Razorpay specific implementation"""
    
    def __init__(self, gateway: PaymentGateway):
        super().__init__(gateway)
        self._setup_client()
    
    def _setup_client(self):
        """Setup Razorpay client"""
        import razorpay
        self.client = razorpay.Client(
            auth=(
                self.credentials.get('key_id'),
                self.credentials.get('key_secret')
            )
        )
    
    def initiate_payment(self, payment, redirect_url: str) -> Dict[str, Any]:
        """Initiate Razorpay payment"""
        try:
            order_data = {
                'amount': int(payment.amount * 100), 
                'currency': 'INR',
                'receipt': payment.merchant_transaction_id,
                'payment_capture': 1
            }
            
            order = self.client.order.create(data=order_data)
            
            PaymentGatewayManager.log_gateway_action(
                gateway=self.gateway,
                action='order_created',
                request_data=order_data,
                response_data=order,
                status='success',
                payment=payment
            )
            
            return {
                'success': True,
                'order_id': order['id'],
                'key_id': self.credentials.get('key_id'),
                'amount': order['amount'],
                'currency': order['currency']
            }
            
        except Exception as e:
            PaymentGatewayManager.log_gateway_action(
                gateway=self.gateway,
                action='order_creation_failed',
                status='failed',
                error_message=str(e),
                payment=payment
            )
            raise


class StripeGatewayClient(BaseGatewayClient):
    """Stripe specific implementation"""
    
    def __init__(self, gateway: PaymentGateway):
        super().__init__(gateway)
        self._setup_client()
    
    def _setup_client(self):
        """Setup Stripe client"""
        import stripe
        stripe.api_key = self.credentials.get('secret_key')
        self.stripe = stripe
    
    def initiate_payment(self, payment, redirect_url: str) -> Dict[str, Any]:
        """Initiate Stripe payment"""
        try:
            session = self.stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'inr',
                        'product_data': {
                            'name': payment.payment_metadata.get('description', 'Payment'),
                        },
                        'unit_amount': int(payment.amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=redirect_url + '?status=success',
                cancel_url=redirect_url + '?status=cancelled',
                metadata={
                    'merchant_transaction_id': payment.merchant_transaction_id
                }
            )
            
            return {
                'success': True,
                'session_id': session.id,
                'redirect_url': session.url
            }
            
        except Exception as e:
            logger.error(f"Stripe payment initiation failed: {e}")
            raise


# Similar implementations for Paytm and Cashfree...
class PaytmGatewayClient(BaseGatewayClient):
    pass

class CashfreeGatewayClient(BaseGatewayClient):
    pass