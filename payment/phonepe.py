import os
import time
import uuid
import json
import logging
from decimal import Decimal
from typing import Dict

# Django standard imports
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

# Third-party PhonePe SDK imports
from phonepe.sdk.pg.env import Env
from phonepe.sdk.pg.payments.v2.standard_checkout_client import StandardCheckoutClient
from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import StandardCheckoutPayRequest
from phonepe.sdk.pg.common.models.request.meta_info import MetaInfo
from phonepe.sdk.pg.common.exceptions import PhonePeException

# Payment gateway and models
from payment.gateway_manager import PaymentGatewayManager
from .models import Payment, Transaction, PaymentLog
from .exceptions import PaymentError, InvalidPaymentError
from .utils import validate_amount, sanitize_user_input, get_client_ip

# User related models
from user.models import Order, OrderItem, ProductVariant, ShippingAddress

# Django REST Framework imports
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status




logger = logging.getLogger(__name__)


class ListPaymentGatewaysView(APIView):
    """List all available payment gateways"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        gateways = PaymentGatewayManager.get_active_gateways()
        
        gateway_data = []
        for gateway in gateways:
            gateway_data.append({
                'id': gateway.id,
                'name': gateway.name,
                'display_name': gateway.display_name,
                'description': gateway.description,
                'logo': gateway.logo.url if gateway.logo else None,
                'is_default': gateway.is_default,
                'min_amount': str(gateway.min_amount),
                'max_amount': str(gateway.max_amount) if gateway.max_amount else None,
                'features': {
                    'supports_refund': gateway.supports_refund,
                    'supports_upi': gateway.supports_upi,
                    'supports_cards': gateway.supports_cards,
                    'supports_netbanking': gateway.supports_netbanking,
                    'supports_wallets': gateway.supports_wallets,
                },
                'transaction_fee': {
                    'percentage': str(gateway.transaction_fee_percentage),
                    'fixed': str(gateway.transaction_fee_fixed),
                }
            })
        
        return Response({
            'gateways': gateway_data,
            'default_gateway': next(
                (g['name'] for g in gateway_data if g['is_default']), 
                None
            )
        })


def get_phonepe_client():
    try:
        env_str = os.environ.get("PHONEPE_ENV", getattr(settings, "PHONEPE_ENV", "SANDBOX"))
        env = Env.SANDBOX if env_str.upper() == "SANDBOX" else Env.PRODUCTION
        client_id = os.environ.get("PHONEPE_CLIENT_ID", getattr(settings, "PHONEPE_CLIENT_ID", None))
        print(client_id,'id clikent')
        client_secret = os.environ.get("PHONEPE_CLIENT_SECRET", getattr(settings, "PHONEPE_CLIENT_SECRET", None))
        version_raw = os.environ.get("PHONEPE_CLIENT_VERSION", getattr(settings, "PHONEPE_CLIENT_VERSION", 1))
        client_version = int(version_raw) if str(version_raw).isdigit() else 1

        if not all([client_id, client_secret]):
            raise ValueError("Missing required PhonePe credentials: CLIENT_ID, CLIENT_SECRET")

        return StandardCheckoutClient.get_instance(
            client_id=client_id,
            client_secret=client_secret,
            client_version=client_version,
            env=env,
            should_publish_events=False
        )
    except Exception as e:
        logger.error(f"Failed to initialize PhonePe client: {e}")
        raise PaymentError(f"Payment system configuration error: {e}")


@login_required
@require_POST
def place_order_view(request):
    """
    Place an order for the currently authenticated user.
    Expects POST data:
        - shipping_address_id
        - items: list of dicts serialized as JSON, each dict: {variant_id, quantity}
        - coupon_id (optional)
    """
    try:
        shipping_address_id = request.POST.get('shipping_address_id')
        items_json = request.POST.get('items')
        coupon_id = request.POST.get('coupon_id')

        if not shipping_address_id or not items_json:
            messages.error(request, "Shipping address and items are required.", extra_tags='order-error')
            return redirect('cart_view')

        try:
            items = json.loads(items_json)
        except Exception:
            messages.error(request, "Invalid items format.", extra_tags='order-error')
            return redirect('cart_view')

        if not items or not isinstance(items, list):
            messages.error(request, "Cart is empty or invalid.", extra_tags='order-error')
            return redirect('cart_view')

        shipping_address = get_object_or_404(ShippingAddress, id=shipping_address_id, user=request.user)

        coupon = None
        if coupon_id:
            from leafin_backend.user.models import Coupon
            try:
                coupon = Coupon.objects.get(id=coupon_id, is_active=True)
            except Coupon.DoesNotExist:
                coupon = None

        total = Decimal("0.00")
        order_items = []
        for item in items:
            variant_id = item.get('variant_id')
            quantity = int(item.get('quantity', 1))
            if not variant_id or quantity < 1:
                continue
            variant = get_object_or_404(ProductVariant, id=variant_id)
            price = variant.price if hasattr(variant, 'price') else Decimal("0.00")
            subtotal = price * quantity
            total += subtotal
            order_items.append({'variant': variant, 'quantity': quantity, 'price': price})

        if not order_items:
            messages.error(request, "No valid items to order.", extra_tags='order-error')
            return redirect('cart_view')

        if coupon:
            discount = total * (coupon.discount_percentage / Decimal("100"))
            total -= discount

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                shipping_address=shipping_address,
                status='pending',
                total_amount=total,
                coupon=coupon
            )
            for oi in order_items:
                OrderItem.objects.create(
                    order=order,
                    variant=oi['variant'],
                    quantity=oi['quantity'],
                    price=oi['price']
                )
            order.calculate_total()

        messages.success(request, f"Order placed successfully! Your order number is #{order.id}.", extra_tags='order-success')
        return redirect('order_detail', order_id=order.id)

    except Exception as e:
        logger.exception(f"Failed to place order for user {request.user}: {e}")
        messages.error(request, "Could not place order. Please try again.", extra_tags='order-error')
        return redirect('cart_view')


class PaymentManager:
    @staticmethod
    def create_payment(user, amount: Decimal, paid_for=None, order=None, **kwargs) -> Payment:
        with transaction.atomic():
            payment_data = {
                'user': user,
                'amount': amount,
                'status': 'initiated',
                'merchant_transaction_id': str(uuid.uuid4()),
                'payment_method': 'phonepe',
                'initiated_at': timezone.now(),
                'ip_address': kwargs.get('ip_address'),
                'user_agent': kwargs.get('user_agent', '')[:500],
            }

            if paid_for:
                from django.contrib.contenttypes.models import ContentType
                payment_data['content_type'] = ContentType.objects.get_for_model(paid_for)
                payment_data['object_id'] = paid_for.pk

            payment_data.update({
                'customer_phone': kwargs.get('customer_phone', ''),
                'customer_email': kwargs.get('customer_email', ''),
                'customer_name': kwargs.get('customer_name', ''),
                'payment_metadata': kwargs.get('metadata', {}),
            })

            # Associate an order if provided
            if order is not None:
                payment_data['order'] = order

            payment = Payment.objects.create(**payment_data)
            print(f"Payment created with merchant_transaction_id: {payment.merchant_transaction_id}")

            PaymentLog.log_payment_event(
                payment=payment,
                action='payment_initiated',
                details={
                    'amount': str(amount),
                    'method': 'phonepe',
                    'sdk_version': 'v2',
                    'description': kwargs.get('description', '')
                },
                user=user,
                ip_address=kwargs.get('ip_address')
            )
            return payment

    @staticmethod
    def create_transaction(payment: Payment, **kwargs) -> Transaction:
        with transaction.atomic():
            transaction_obj = Transaction.objects.create(
                payment=payment,
                order_id=payment.merchant_transaction_id,
                transaction_id=kwargs.get('transaction_id', ''),
                payment_method=payment.payment_method,
                amount=payment.amount,
                status=kwargs.get('status', 'pending'),
                gateway_response=kwargs.get('gateway_response', {}),
                ip_address=kwargs.get('ip_address'),
            )
            print(f"Transaction created for payment {payment.merchant_transaction_id} with transaction_id: {transaction_obj.transaction_id}, status: {transaction_obj.status}")
            PaymentLog.log_payment_event(
                payment=payment,
                action='transaction_created',
                details={
                    'transaction_db_id': transaction_obj.id,
                    'transaction_status': transaction_obj.status,
                    'sdk_used': True
                },
                user=payment.user,
                ip_address=kwargs.get('ip_address')
            )
            return transaction_obj

    @staticmethod
    def update_payment_status(payment: Payment, status: str,
                             gateway_data: Dict = None,
                             phonepe_transaction_id: str = None) -> Payment:
        # from dashboard.utils import create_notification
        with transaction.atomic():
            old_status = payment.status
            payment.status = status
            print(f"status changed from {old_status} to {status}")

            # Set completion timestamps
            if status == 'completed' and not payment.completed_at:
                payment.completed_at = timezone.now()
            elif status == 'failed' and not payment.failed_at:
                payment.failed_at = timezone.now()

            payment.save()
            if payment.transactions.exists():
                latest_transaction = payment.transactions.latest('created_at')
                latest_transaction.status = status
                latest_transaction.payment_mode = gateway_data.get('payment_mode', 'no data') if gateway_data else None
                if phonepe_transaction_id:
                    latest_transaction.transaction_id = phonepe_transaction_id
                if gateway_data:
                    latest_transaction.gateway_response = gateway_data
                    latest_transaction.update_from_phonepe_response(gateway_data)
                    if latest_transaction.status != status:
                        print(f"Forcing transaction status from {latest_transaction.status} to {status}")
                        latest_transaction.status = status
                latest_transaction.save()
                print(f"Transaction {latest_transaction.id} final status: {latest_transaction.status}")
            else:
                new_transaction = PaymentManager.create_transaction(
                    payment=payment,
                    transaction_id=phonepe_transaction_id or '',
                    gateway_response=gateway_data or {},
                    payment_mode=gateway_data.get('payment_mode', 'no data') if gateway_data else None,
                    status=status
                )
                print(f"New transaction {new_transaction.id} created with status: {new_transaction.status}")

            # Update related Order status if the payment was for an order
            if hasattr(payment, "order") and payment.order:
                order = payment.order
                if status == "completed":
                    order.status = "processing"
                elif status == "failed":
                    order.status = "cancelled"
                order.save()

            log_details = {
                'old_status': old_status,
                'new_status': status,
                'gateway_data_received': bool(gateway_data),
                'phonepe_transaction_id': phonepe_transaction_id
            }

            if gateway_data:
                serializable_gateway_data = {}
                for key, value in gateway_data.items():
                    try:
                        json.dumps(value)
                        serializable_gateway_data[key] = value
                    except (TypeError, ValueError):
                        serializable_gateway_data[key] = str(value)
                log_details['gateway_data_sample'] = serializable_gateway_data

            PaymentLog.log_payment_event(
                payment=payment,
                action='status_updated',
                details=log_details,
                user=payment.user
            )

            return payment



@method_decorator(csrf_exempt, name='dispatch')
class InitiatePhonePePaymentView(APIView):
    authentication_classes = [JWTAuthentication, SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            data = request.data if hasattr(request, "data") else request.POST

            print(data.get("amount", ""))
            order_id = data.get("order_id")
            amount_str = sanitize_user_input(data.get("amount", ""))
            description = sanitize_user_input(data.get("description", ""))
            customer_phone = sanitize_user_input(data.get("phone", ""))

            if not order_id and not amount_str:
                return Response({"error": "order_id or amount is required"}, status=status.HTTP_400_BAD_REQUEST)

            paid_for_obj = None
            order_obj = None

            if order_id:
                try:
                    order_obj = Order.objects.get(id=order_id, user=request.user)
                    amount = order_obj.total_amount
                    paid_for_obj = order_obj
                except Order.DoesNotExist:
                    return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
            else:
                try:
                    amount = validate_amount(amount_str)
                    print(amount,'aaaa')
                except Exception as e:
                    return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            if not amount or amount <= 0:
                return Response({"error": "A positive amount is required."}, status=status.HTTP_400_BAD_REQUEST)

            # Optional: Check for content_type/object_id support, unused in common mobile flow
            if data.get('content_type_id') and data.get('object_id'):
                try:
                    content_type = ContentType.objects.get(id=data['content_type_id'])
                    object_id = int(data['object_id'])
                    paid_for_obj = content_type.get_object_for_this_type(id=object_id)
                except (ContentType.DoesNotExist, Exception) as e:
                    logger.warning(f"Invalid content type reference: {e}")
                    return Response({'error': 'Invalid content type or object id'}, status=400)

            # Rate limiting check (5 sec holdout, for example)
            cache_key = f"payment_initiation_{request.user.id}"
            if cache.get(cache_key):
                return Response({"error": "Please wait before initiating another payment."},
                                status=status.HTTP_429_TOO_MANY_REQUESTS)
            cache.set(cache_key, True, timeout=5) 

            payment = PaymentManager.create_payment(
                user=request.user,
                amount=amount,
                paid_for=paid_for_obj,
                order=order_obj,
                customer_phone=customer_phone,
                customer_email=request.user.email,
                customer_name=request.user.get_full_name(),
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metadata={'description': description},
                description=description
            )

            transaction_obj = PaymentManager.create_transaction(
                payment=payment,
                ip_address=get_client_ip(request),
            )

            client = get_phonepe_client()

            
            frontend_callback_url = data.get("redirect_url") or request.build_absolute_uri(f"/pay/status/{payment.merchant_transaction_id}/")

            # In production, send a callback/redirect URL for status check (ideally coming from your React app's config)
            meta_info = MetaInfo(udf1=description[:100] if description else "Payment")

            pay_request = StandardCheckoutPayRequest.build_request(
                merchant_order_id=payment.merchant_transaction_id,
                amount=int(amount * 100),
                redirect_url=frontend_callback_url,
                meta_info=meta_info,
            )

            try:
                pay_response = client.pay(pay_request)
            except Exception as sdk_exc:
                return Response({"error": f"Payment Gateway error: {str(sdk_exc)}"}, status=status.HTTP_502_BAD_GATEWAY)

            PaymentManager.update_payment_status(payment, 'pending', gateway_data=None, phonepe_transaction_id=None)

            PaymentLog.log_payment_event(
                payment=payment,
                action='sdk_pay_request',
                details={
                    'redirect_url_received': bool(getattr(pay_response, "redirect_url", None)),
                    'amount_paisa': int(amount * 100),
                },
                user=request.user,
                ip_address=get_client_ip(request)
            )

            if getattr(pay_response, 'redirect_url', None):
                logger.info(f"Payment initiated successfully: {payment.merchant_transaction_id}")
                return Response({
                    "payment_id": payment.id,
                    "merchant_transaction_id": payment.merchant_transaction_id,
                    "redirect_url": pay_response.redirect_url,
                    "status": "initiated"
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {"error": "No redirect URL received from PhonePe."},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        except InvalidPaymentError as e:
            logger.warning(f"Invalid payment request: {e}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except PaymentError as e:
            logger.error(f"Payment initiation failed: {e}")
            return Response({"error": "Payment initiation failed. Please try again."},
                            status=status.HTTP_502_BAD_GATEWAY)

        except Exception as e:
            logger.exception("Unexpected error during payment initiation")
            return Response({"error": "An unexpected error occurred. Please try again."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class PaymentStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, merchant_transaction_id=None, *args, **kwargs):
        return self.handle_status_check(request, merchant_transaction_id)

    def post(self, request, merchant_transaction_id=None, *args, **kwargs):
        if not merchant_transaction_id:
            merchant_transaction_id = request.data.get("merchantTransactionId")
        return self.handle_status_check(request, merchant_transaction_id)

    def handle_status_check(self, request, merchant_transaction_id):
        try:
            if not merchant_transaction_id:
                return Response(
                    {"error": "Invalid payment session.", "status": "error"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                payment = (
                    Payment.objects.select_related("user")
                    .prefetch_related("transactions")
                    .get(merchant_transaction_id=merchant_transaction_id)
                )
            except Payment.DoesNotExist:
                return Response(
                    {"error": "Payment session not found.", "status": "error"},
                    status=status.HTTP_404_NOT_FOUND
                )

            transaction_id = None
            payment_mode = payment.payment_method
            phonepe_state = None

            # Check for pending/initiated
            if payment.status in ["pending", "initiated"]:
                try:
                    client = get_phonepe_client()
                    resp = client.get_order_status(payment.merchant_transaction_id, details=False)
                    if resp.payment_details and len(resp.payment_details) > 0:
                        payment_mode = getattr(resp.payment_details[0], 'payment_mode', payment.payment_method)
                        transaction_id = getattr(resp.payment_details[0], 'transaction_id', None)
                    phonepe_state = str(resp.state).lower()

                    state_map = {
                        "completed": "completed",
                        "success": "completed",
                        "failed": "failed",
                        "cancelled": "failed",
                        "pending": "pending",
                        "created": "initiated",
                    }
                    new_status = state_map.get(phonepe_state, payment.status)
                    if new_status != payment.status:
                        gateway_data = {
                            'state': phonepe_state,
                            'response_code': str(getattr(resp, 'response_code', '')),
                            'transaction_id': transaction_id,
                            'amount': str(getattr(resp, 'amount', '')),
                            'payment_mode': payment_mode,
                            'merchant_id': str(getattr(resp, 'merchant_id', '')),
                            'merchant_transaction_id': str(getattr(resp, 'merchant_transaction_id', '')),
                        }
                        PaymentManager.update_payment_status(
                            payment=payment,
                            status=new_status,
                            gateway_data=gateway_data,
                            phonepe_transaction_id=transaction_id
                        )
                        payment.refresh_from_db()
                except Exception as e:
                    logger.error(f"SDK status check failed: {e}")
                    PaymentLog.log_payment_event(
                        payment=payment,
                        action="status_check_failed",
                        details={"error": str(e)},
                        user=getattr(request, "user", None),
                        level="error",
                    )

            latest_transaction = None
            try:
                latest_transaction = payment.transactions.order_by("-created_at").first()
            except Exception:
                latest_transaction = None

            order_obj = getattr(payment, "order", None)
            response_data = {
                "merchant_transaction_id": payment.merchant_transaction_id,
                "payment_status": payment.status,
                "amount": payment.get_display_amount(),
                "transaction_id": (latest_transaction.transaction_id if latest_transaction else payment.merchant_transaction_id),
                "paid_for": str(payment.paid_for) if payment.paid_for else None,
                "payment_date": str((latest_transaction.created_at if latest_transaction and latest_transaction.status == "completed" else payment.completed_at) or payment.created_at),
                "payment_method": (getattr(latest_transaction, "payment_mode", None) if latest_transaction else payment.payment_method),
                "amount_paid": (str(latest_transaction.amount) if latest_transaction else str(payment.amount)),
                "order": getattr(order_obj, "id", None) if order_obj else None,
                "order_status": getattr(order_obj, "status", None) if order_obj else None,
                "user": {
                    "id": payment.user.id,
                    "name": payment.user.get_full_name(),
                    "email": payment.user.email,
                    "phone": getattr(payment.user, "phone_number", None),
                } if payment.user else None,
                "gateway_state": phonepe_state,
            }

            if payment.status == "completed":
                response_data["message"] = f"Payment of {payment.get_display_amount()} completed successfully!"
                return Response(response_data, status=status.HTTP_200_OK)
            elif payment.status == "failed":
                response_data["message"] = "Payment failed. Please try again or contact support."
                return Response(response_data, status=status.HTTP_200_OK)
            elif payment.status in ["pending", "initiated"]:
                response_data["message"] = "Payment is being processed. Please wait..."
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                response_data["message"] = "Payment status is being verified. Please wait..."
                return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error checking payment status")
            return Response(
                {
                    "error": "Unable to verify payment status. Please contact support.",
                    "merchant_transaction_id": merchant_transaction_id,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@require_http_methods(["POST"])
@csrf_exempt
def phonepe_webhook(request):
    try:
        webhook_start_time = time.time()
        client_ip = get_client_ip(request)

        print("=== PhonePe Webhook Received ===")

        raw_body = request.body.decode("utf-8")
        authorization_header = request.headers.get('Authorization', '')

        print(f"Raw body: {raw_body}")
        print(f"Authorization header: {authorization_header[:20]}...")

        if not raw_body or not authorization_header:
            logger.error("Missing raw body or authorization header")
            return Response({"error": "Missing required data"}, status=400)

        callback_response = validate_phonepe_webhook_with_sdk(
            authorization_header=authorization_header,
            raw_body=raw_body
        )

        if not callback_response:
            logger.warning("Webhook SDK validation failed")
            print("Webhook: SDK validation failed - discarding webhook")
            return Response({"error": "Webhook validation failed"}, status=401)

        print(f"Webhook validated successfully - Callback Type: {callback_response.type}")

        if callback_response.type in ['CHECKOUT_ORDER_COMPLETED', 'CHECKOUT_ORDER_FAILED']:
            return process_payment_callback(callback_response, client_ip, webhook_start_time)
        elif callback_response.type in ['PG_REFUND_COMPLETED', 'PG_REFUND_FAILED', 'PG_REFUND_ACCEPTED']:
            return process_refund_callback(callback_response, client_ip, webhook_start_time)
        else:
            logger.info(f"Unknown callback type: {callback_response.type}")
            print(f"Webhook: Unknown callback type {callback_response.type}")
            return Response({"success": True, "message": "Unknown callback type processed"}, status=200)

    except Exception as e:
        logger.exception("Critical error processing PhonePe webhook")
        print(f"Webhook critical error: {e}")
        return Response({"error": "Internal server error"}, status=500)


def validate_phonepe_webhook_with_sdk(authorization_header, raw_body):

    try:
        username = (
            os.environ.get('PHONEPE_WEBHOOK_USERNAME') or
            getattr(settings, 'PHONEPE_WEBHOOK_USERNAME', '')
        )
        password = (
            os.environ.get('PHONEPE_WEBHOOK_PASSWORD') or
            getattr(settings, 'PHONEPE_WEBHOOK_PASSWORD', '')
        )

        if not username or not password:
            print("Webhook validation: Missing credentials")
            return None

        client = get_phonepe_client()
        callback_response = client.validate_callback(
            username=username,
            password=password,
            callback_header_data=authorization_header,
            callback_response_data=raw_body
        )

        print(f"SDK validation successful - Type: {callback_response.type}")
        return callback_response

    except PhonePeException as e:
        logger.error(f"PhonePe SDK validation error: {e.code} - {e.message}")
        print(f"SDK validation error: {e.code} - {e.message}")
        print(f"HTTP status: {e.http_status_code}")
        print(f"Error data: {e.data}")
        return None
    except Exception as e:
        logger.error(f"Webhook validation error: {e}")
        print(f"Webhook validation error: {e}")
        return None


def process_payment_callback(callback_response, client_ip, webhook_start_time):
    try:
        callback_data = callback_response.payload
        callback_type = callback_response.type

        merchant_transaction_id = getattr(callback_data, 'original_merchant_order_id', None)
        phonepe_order_id = getattr(callback_data, 'order_id', None)
        payment_state = getattr(callback_data, 'state', None)
        amount = getattr(callback_data, 'amount', None)

        print(f"Payment callback - Transaction: {merchant_transaction_id}, State: {payment_state}, Type: {callback_type}")

        if not merchant_transaction_id or not payment_state:
            logger.error("Missing required fields in payment callback")
            return Response({"error": "Missing required fields"}, status=400)

        try:
            payment = Payment.objects.get(merchant_transaction_id=merchant_transaction_id)
            print(f"Payment callback: Found payment {payment.id}")
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for transaction: {merchant_transaction_id}")
            return Response({"error": "Payment not found"}, status=404)

        if callback_type == 'CHECKOUT_ORDER_COMPLETED' and payment_state.upper() == 'COMPLETED':
            new_status = 'completed'
        elif callback_type == 'CHECKOUT_ORDER_FAILED' or payment_state.upper() == 'FAILED':
            new_status = 'failed'
        else:
            new_status = 'pending'

        old_status = payment.status

        if old_status != new_status:
            print(f"Payment callback: Updating status from {old_status} to {new_status}")

            gateway_data = {
                'callback_type': callback_type,
                'state': payment_state,
                'phonepe_order_id': phonepe_order_id,
                'amount': amount,
                'merchant_id': getattr(callback_data, 'merchant_id', ''),
                'webhook_timestamp': time.time()
            }

            payment_details = getattr(callback_data, 'payment_details', None)
            if payment_details and len(payment_details) > 0:
                payment_detail = payment_details[0]
                gateway_data.update({
                    'transaction_id': getattr(payment_detail, 'transaction_id', ''),
                    'payment_mode': getattr(payment_detail, 'payment_mode', ''),
                    'payment_timestamp': getattr(payment_detail, 'timestamp', '')
                })

            if new_status == 'failed':
                gateway_data.update({
                    'error_code': getattr(callback_data, 'error_code', ''),
                    'detailed_error_code': getattr(callback_data, 'detailed_error_code', '')
                })

            expire_at = getattr(callback_data, 'expire_at', None)
            if expire_at:
                gateway_data['expire_at'] = expire_at

            PaymentManager.update_payment_status(
                payment=payment,
                status=new_status,
                gateway_data=gateway_data,
                phonepe_transaction_id=gateway_data.get('transaction_id', '')
            )
        else:
            print(f"Payment callback: Status unchanged ({old_status})")

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

        logger.info(f"Payment callback processed: {merchant_transaction_id} -> {new_status}")
        print(f"Payment callback: Processed in {processing_time:.2f}ms")

        return Response({
            "success": True,
            "status": "processed",
            "payment_status": new_status,
            "processing_time_ms": round(processing_time, 2)
        }, status=200)

    except Exception as e:
        logger.exception("Error processing payment callback")
        print(f"Payment callback error: {e}")
        return Response({"error": "Payment callback processing failed"}, status=500)


def process_refund_callback(callback_response, client_ip, webhook_start_time):
    try:
        callback_data = callback_response.payload
        callback_type = callback_response.type

        merchant_refund_id = getattr(callback_data, 'merchant_refund_id', None)
        phonepe_refund_id = getattr(callback_data, 'refund_id', None)
        refund_state = getattr(callback_data, 'state', None)
        amount = getattr(callback_data, 'amount', None)

        print(f"Refund callback - RefundId: {merchant_refund_id}, State: {refund_state}, Type: {callback_type}")
        processing_time = (time.time() - webhook_start_time) * 1000
        logger.info(f"Refund callback received: {merchant_refund_id} -> {refund_state}")
        print(f"Refund callback: Processed in {processing_time:.2f}ms")

        return Response({
            "success": True,
            "status": "refund_callback_processed",
            "refund_status": refund_state,
            "processing_time_ms": round(processing_time, 2)
        }, status=200)

    except Exception as e:
        logger.exception("Error processing refund callback")
        print(f"Refund callback error: {e}")
        return Response({"error": "Refund callback processing failed"}, status=500)


@method_decorator([login_required, require_http_methods(["GET"])], name='dispatch')
class PaymentHistoryView(View):
    def get(self, request, *args, **kwargs):
        payments_queryset = Payment.objects.filter(
            user=request.user
        ).select_related('content_type', 'order').prefetch_related('transactions').order_by('-created_at')

        status_filter = request.GET.get('status')
        if status_filter and status_filter in ['completed', 'failed', 'pending', 'initiated']:
            payments_queryset = payments_queryset.filter(status=status_filter)

        search_query = request.GET.get('search')
        if search_query:
            try:
                search_amount = Decimal(search_query)
                payments_queryset = payments_queryset.filter(amount=search_amount)
            except:
                payments_queryset = payments_queryset.filter(
                    payment_metadata__description__icontains=search_query
                )

        # Pagination
        paginator = Paginator(payments_queryset, 10)
        page = request.GET.get('page')

        try:
            payments_page = paginator.page(page)
        except PageNotAnInteger:
            payments_page = paginator.page(1)
        except EmptyPage:
            payments_page = paginator.page(paginator.num_pages)

        all_payments = Payment.objects.filter(user=request.user)
        stats = {
            'total_payments': all_payments.count(),
            'successful_payments': all_payments.filter(status='completed').count(),
            'total_amount_paid': sum(p.amount for p in all_payments.filter(status='completed')),
            'pending_payments': all_payments.filter(status__in=['pending', 'initiated']).count(),
        }

        context = {
            'payments': payments_page,
            'stats': stats,
            'current_filters': {
                'status': status_filter,
                'search': search_query,
            }
        }
        print("Payment history flow: rendering payment history page")
        return render(request, "payment/payment_history.html", context)

@method_decorator(login_required, name='dispatch')
class PaymentDetailView(View):

    def get(self, request, merchant_transaction_id, *args, **kwargs):
        try:
            payment = get_object_or_404(
                Payment.objects.select_related('user', 'content_type', 'order')
                              .prefetch_related('transactions', 'logs'),
                merchant_transaction_id=merchant_transaction_id,
                user=request.user
            )

            order_obj = getattr(payment, "order", None)
            context = {
                'payment': payment,
                'transactions': payment.transactions.all().order_by('-created_at'),
                'recent_logs': payment.logs.all().order_by('-created_at')[:10],
                'can_retry': payment.status == 'failed',
                'payment_metadata': payment.payment_metadata,
                'order': order_obj,
            }
            print(f"Payment detail flow: rendering detail for payment {merchant_transaction_id}")
            return render(request, "payment/payment_detail.html", context)

        except Exception as e:
            logger.exception(f"Error displaying payment detail: {e}")
            print(f"Payment detail flow: Exception occurred - {e}")
            messages.error(request, "Payment details not found.")
            return redirect('payment:history')

@method_decorator([login_required, require_http_methods(["GET"])], name='dispatch')
class PaymentDashboardView(View):

    def get(self, request, *args, **kwargs):
        user_payments = Payment.objects.filter(user=request.user)

        stats = {
            'total_payments': user_payments.count(),
            'successful_payments': user_payments.filter(status='completed').count(),
            'failed_payments': user_payments.filter(status='failed').count(),
            'pending_payments': user_payments.filter(status__in=['pending', 'initiated']).count(),
            'total_amount_paid': sum(p.amount for p in user_payments.filter(status='completed')),
            'recent_payments': user_payments.order_by('-created_at')[:5],
            'this_month_payments': user_payments.filter(
                created_at__month=timezone.now().month,
                created_at__year=timezone.now().year
            ).count(),
            'success_rate': 0,
        }

        if stats['total_payments'] > 0:
            stats['success_rate'] = round(
                (stats['successful_payments'] / stats['total_payments']) * 100, 1
            )

        context = {
            'stats': stats,
            'user': request.user,
        }
        print("Payment dashboard flow: rendering dashboard")
        return render(request, "payment/dashboard.html", context)


def get_payment_stats_for_admin():
    from django.db.models import Count, Sum

    stats = Payment.objects.aggregate(
        total_payments=Count('id'),
        total_amount=Sum('amount'),
        successful_payments=Count('id', filter=Q(status='completed')),
        failed_payments=Count('id', filter=Q(status='failed')),
    )
    print("Admin stats flow: returning payment stats")
    return stats

def retry_failed_payment(payment_id: int, user) -> bool:
    try:
        payment = Payment.objects.get(id=payment_id, user=user, status='failed')

        order = getattr(payment, "order", None)
        new_payment = PaymentManager.create_payment(
            user=payment.user,
            amount=payment.amount,
            paid_for=payment.paid_for,
            order=order,
            customer_phone=payment.customer_phone,
            customer_email=payment.customer_email,
            customer_name=payment.customer_name,
            metadata=payment.payment_metadata
        )
        print(f"Retry payment flow: Retried payment created with id {new_payment.id}")
        PaymentLog.log_payment_event(
            payment=new_payment,
            action='payment_retry',
            details={'original_payment_id': payment_id},
            user=user
        )

        return True
    except Exception as e:
        logger.error(f"Failed to retry payment {payment_id}: {e}")
        print(f"Retry payment flow: Exception occurred - {e}")
        return False